"""
検査実行API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import json
import logging
from datetime import datetime

from app.database import get_db
from app.models.inspection import (
    InspectionTarget,
    InspectionItem,
    InspectionExecution,
    InspectionItemExecution,
    InspectionResult,
)
from app.schemas.inspection import (
    InspectionExecutionCreate,
    InspectionExecutionResponse,
    InspectionItemExecutionResponse,
    InspectionResultCreate,
    InspectionResultResponse,
    ExecuteInspectionRequest,
    ExecuteInspectionResponse,
    SaveInspectionResultRequest,
    PaginatedResponse,
    JudgmentResult,
    InspectionStatus,
    InspectionItemStatus,
    AIResult,
    HumanResult,
)
from app.services.auth_service import get_current_user
from app.services.inspection_executor import InspectionExecutor
from app.services.grpc_pipeline_executor import GRPCPipelineExecutor

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_user_id(current_user) -> Optional[uuid.UUID]:
    try:
        if isinstance(current_user, dict):
            val = current_user.get("id")
            return uuid.UUID(val) if isinstance(val, str) else val
        val = getattr(current_user, "id", None)
        return uuid.UUID(val) if isinstance(val, str) else val
    except Exception:
        return None


@router.post(
    "/executions",
    response_model=ExecuteInspectionResponse,
    tags=["inspection-execution"],
)
async def create_inspection_execution(
    request: ExecuteInspectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査実行を開始"""
    try:
        # 検査対象存在チェック
        target = await db.execute(
            select(InspectionTarget)
            .options(selectinload(InspectionTarget.inspection_items))
            .where(InspectionTarget.id == request.target_id)
        )
        target = target.scalar_one_or_none()

        if not target:
            raise HTTPException(status_code=404, detail="Inspection target not found")

        if not target.inspection_items:
            raise HTTPException(
                status_code=400, detail="No inspection items defined for this target"
            )

        # 検査実行を作成
        execution = InspectionExecution(
            target_id=request.target_id,
            operator_id=request.operator_id or _extract_user_id(current_user),
            qr_code=request.qr_code,
            metadata=request.metadata or {},
            status=InspectionStatus.PENDING,
        )

        db.add(execution)
        await db.flush()  # IDを取得するためフラッシュ

        # 検査項目実行を事前作成
        item_executions = []
        for item in sorted(target.inspection_items, key=lambda x: x.execution_order):
            item_execution = InspectionItemExecution(
                execution_id=execution.id,
                item_id=item.id,
                status=InspectionItemStatus.ITEM_PENDING,
            )
            db.add(item_execution)
            item_executions.append(item_execution)

        await db.commit()
        await db.refresh(execution)

        # レスポンス用にtargetをロード
        await db.refresh(execution, ["target"])

        logger.info(
            f"Created inspection execution: {execution.id} for target: {request.target_id}"
        )

        return ExecuteInspectionResponse(execution_id=execution.id, execution=execution)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create inspection execution: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/executions/{execution_id}",
    response_model=InspectionExecutionResponse,
    tags=["inspection-execution"],
)
async def get_inspection_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査実行を取得"""
    try:
        execution = await db.execute(
            select(InspectionExecution)
            .options(
                selectinload(InspectionExecution.target),
                selectinload(InspectionExecution.item_executions).selectinload(
                    InspectionItemExecution.item
                ),
            )
            .where(InspectionExecution.id == execution_id)
        )
        execution = execution.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=404, detail="Inspection execution not found"
            )

        return execution

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inspection execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/executions",
    response_model=PaginatedResponse[InspectionExecutionResponse],
    tags=["inspection-execution"],
)
async def list_inspection_executions(
    target_id: Optional[uuid.UUID] = Query(None),
    operator_id: Optional[uuid.UUID] = Query(None),
    status: Optional[InspectionStatus] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査実行一覧を取得"""
    try:
        # ベースクエリ
        query = select(InspectionExecution).options(
            selectinload(InspectionExecution.target)
        )
        count_query = select(func.count(InspectionExecution.id))

        # フィルタ条件
        filters = []
        if target_id:
            filters.append(InspectionExecution.target_id == target_id)
        if operator_id:
            filters.append(InspectionExecution.operator_id == operator_id)
        if status:
            filters.append(InspectionExecution.status == status)
        if from_date:
            filters.append(InspectionExecution.started_at >= from_date)
        if to_date:
            filters.append(InspectionExecution.started_at <= to_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 総件数取得
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # ページング
        offset = (page - 1) * page_size
        query = (
            query.offset(offset)
            .limit(page_size)
            .order_by(InspectionExecution.started_at.desc())
        )

        # データ取得
        result = await db.execute(query)
        executions = result.scalars().all()

        return PaginatedResponse(
            items=executions,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list inspection executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/executions/{execution_id}/items/{item_id}/execute",
    response_model=InspectionItemExecutionResponse,
    tags=["inspection-execution"],
)
async def execute_inspection_item(
    execution_id: uuid.UUID,
    item_id: uuid.UUID,
    image: UploadFile = File(..., description="検査画像"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目を実行（画像アップロード + AI処理）"""
    try:
        # 検査項目実行を取得
        item_execution = await db.execute(
            select(InspectionItemExecution)
            .options(
                selectinload(InspectionItemExecution.item),
                selectinload(InspectionItemExecution.execution),
            )
            .where(
                and_(
                    InspectionItemExecution.execution_id == execution_id,
                    InspectionItemExecution.item_id == item_id,
                )
            )
        )
        item_execution = item_execution.scalar_one_or_none()

        if not item_execution:
            raise HTTPException(
                status_code=404, detail="Inspection item execution not found"
            )

        if item_execution.status not in [
            InspectionItemStatus.ITEM_PENDING,
            InspectionItemStatus.ITEM_FAILED,
        ]:
            raise HTTPException(
                status_code=400, detail="Item execution not in executable state"
            )

        # 画像データを読み込み
        image_data = await image.read()
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")

        # 検査項目実行を更新
        item_execution.status = InspectionItemStatus.ITEM_IN_PROGRESS
        await db.commit()

        # InspectionExecutorを使用してAI処理を実行
        executor = InspectionExecutor(db)

        try:
            # AI処理実行
            ai_result = await executor.execute_ai_inspection(
                item_execution=item_execution,
                image_data=image_data,
                image_format=image.content_type or "image/jpeg",
            )

            # 結果を保存
            item_execution.ai_result = ai_result.dict() if ai_result else None
            item_execution.status = InspectionItemStatus.ITEM_AI_COMPLETED
            item_execution.completed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(item_execution)

            logger.info(
                f"Completed AI inspection for item execution: {item_execution.id}"
            )

            return item_execution

        except Exception as ai_error:
            # AI処理失敗時の処理
            item_execution.status = InspectionItemStatus.ITEM_FAILED
            item_execution.error_message = str(ai_error)
            await db.commit()

            logger.error(
                f"AI inspection failed for item execution {item_execution.id}: {ai_error}"
            )
            raise HTTPException(
                status_code=500, detail=f"AI inspection failed: {ai_error}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute inspection item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/results", response_model=InspectionResultResponse, tags=["inspection-execution"]
)
async def save_inspection_result(
    request: SaveInspectionResultRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査結果を保存"""
    try:
        # 検査項目実行存在チェック
        item_execution = await db.execute(
            select(InspectionItemExecution).where(
                InspectionItemExecution.id == request.item_execution_id
            )
        )
        item_execution = item_execution.scalar_one_or_none()

        if not item_execution:
            raise HTTPException(
                status_code=404, detail="Inspection item execution not found"
            )

        # 既存結果をチェック
        existing_result = await db.execute(
            select(InspectionResult).where(
                InspectionResult.item_execution_id == request.item_execution_id
            )
        )
        existing_result = existing_result.scalar_one_or_none()

        if existing_result:
            # 既存結果を更新
            existing_result.judgment = request.judgment
            existing_result.comment = request.comment
            existing_result.evidence_file_ids = request.evidence_file_ids or []
            existing_result.metrics = request.metrics or {}
            await db.commit()
            await db.refresh(existing_result)
            result = existing_result
        else:
            # 新規結果を作成
            result = InspectionResult(
                execution_id=request.execution_id,
                item_execution_id=request.item_execution_id,
                judgment=request.judgment,
                comment=request.comment,
                evidence_file_ids=request.evidence_file_ids or [],
                metrics=request.metrics or {},
                created_by=_extract_user_id(current_user),
            )
            db.add(result)
            await db.commit()
            await db.refresh(result)

        # 検査項目実行の最終結果を更新
        item_execution.final_result = request.judgment
        if request.judgment in [JudgmentResult.OK, JudgmentResult.NG]:
            item_execution.status = InspectionItemStatus.ITEM_COMPLETED
            item_execution.completed_at = datetime.utcnow()

        await db.commit()

        # すべての項目が完了していれば Execution を COMPLETED へ
        try:
            exec_id = item_execution.execution_id
            total_q = await db.execute(
                select(func.count(InspectionItemExecution.id)).where(
                    InspectionItemExecution.execution_id == exec_id
                )
            )
            done_q = await db.execute(
                select(func.count(InspectionItemExecution.id)).where(
                    and_(
                        InspectionItemExecution.execution_id == exec_id,
                        InspectionItemExecution.status == InspectionItemStatus.ITEM_COMPLETED,
                    )
                )
            )
            total = total_q.scalar() or 0
            done = done_q.scalar() or 0
            if total > 0 and done == total:
                exec_row = (
                    await db.execute(
                        select(InspectionExecution).where(InspectionExecution.id == exec_id)
                    )
                ).scalar_one_or_none()
                if exec_row:
                    exec_row.status = InspectionStatus.COMPLETED
                    exec_row.completed_at = datetime.utcnow()
                    await db.commit()
        except Exception as _:
            # completion 更新の失敗は本処理を妨げない
            pass

        logger.info(f"Saved inspection result: {result.id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save inspection result: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/results",
    response_model=PaginatedResponse[InspectionResultResponse],
    tags=["inspection-execution"],
)
async def list_inspection_results(
    execution_id: Optional[uuid.UUID] = Query(None),
    target_id: Optional[uuid.UUID] = Query(None),
    judgment: Optional[JudgmentResult] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査結果一覧を取得"""
    try:
        # ベースクエリ
        query = select(InspectionResult)
        count_query = select(func.count(InspectionResult.id))

        # フィルタ条件
        filters = []
        if execution_id:
            filters.append(InspectionResult.execution_id == execution_id)
        if judgment:
            filters.append(InspectionResult.judgment == judgment)
        if from_date:
            filters.append(InspectionResult.created_at >= from_date)
        if to_date:
            filters.append(InspectionResult.created_at <= to_date)

        # target_idでフィルタする場合はJOINが必要
        if target_id:
            query = query.join(InspectionExecution).where(
                InspectionExecution.target_id == target_id
            )
            count_query = count_query.join(InspectionExecution).where(
                InspectionExecution.target_id == target_id
            )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 総件数取得
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # ページング
        offset = (page - 1) * page_size
        query = (
            query.offset(offset)
            .limit(page_size)
            .order_by(InspectionResult.created_at.desc())
        )

        # データ取得
        result = await db.execute(query)
        results = result.scalars().all()

        return PaginatedResponse(
            items=results,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list inspection results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/executions/{execution_id}/items",
    response_model=List[InspectionItemExecutionResponse],
    tags=["inspection-execution"],
)
async def get_inspection_item_executions(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査実行の項目実行一覧を取得"""
    try:
        # Join to InspectionItem to sort by its execution_order
        result = await db.execute(
            select(InspectionItemExecution)
            .options(
                selectinload(InspectionItemExecution.item)
                .selectinload(InspectionItem.target),
                selectinload(InspectionItemExecution.item)
                .selectinload(InspectionItem.criteria),
            )
            .join(InspectionItem, InspectionItem.id == InspectionItemExecution.item_id)
            .where(InspectionItemExecution.execution_id == execution_id)
            .order_by(InspectionItem.execution_order.asc())
        )
        item_executions = result.scalars().all()

        return item_executions

    except Exception as e:
        logger.error(f"Failed to get inspection item executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/executions/{execution_id}/status",
    response_model=InspectionExecutionResponse,
    tags=["inspection-execution"],
)
async def update_inspection_execution_status(
    execution_id: uuid.UUID,
    status: InspectionStatus,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査実行ステータスを更新"""
    try:
        execution = await db.execute(
            select(InspectionExecution).where(InspectionExecution.id == execution_id)
        )
        execution = execution.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=404, detail="Inspection execution not found"
            )

        execution.status = status
        if status in [
            InspectionStatus.COMPLETED,
            InspectionStatus.FAILED,
            InspectionStatus.CANCELLED,
        ]:
            execution.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(execution)

        logger.info(f"Updated inspection execution status: {execution_id} -> {status}")
        return execution

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update inspection execution status: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

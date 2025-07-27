"""
検査マスタ管理API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import logging

from app.database import get_db
from app.models.inspection import InspectionTarget, InspectionItem, InspectionCriteria
from app.schemas.inspection import (
    InspectionTargetCreate,
    InspectionTargetUpdate,
    InspectionTargetResponse,
    InspectionItemCreate,
    InspectionItemUpdate,
    InspectionItemResponse,
    InspectionCriteriaCreate,
    InspectionCriteriaUpdate,
    InspectionCriteriaResponse,
    PaginatedResponse,
)
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# 検査対象管理API


@router.post(
    "/targets", response_model=InspectionTargetResponse, tags=["inspection-masters"]
)
async def create_inspection_target(
    target_data: InspectionTargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査対象を作成"""
    try:
        # 重複チェック
        existing = await db.execute(
            select(InspectionTarget).where(
                InspectionTarget.product_code == target_data.product_code
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Product code already exists")

        target = InspectionTarget(
            name=target_data.name,
            description=target_data.description,
            product_code=target_data.product_code,
            version=target_data.version,
            metadata=target_data.metadata or {},
            created_by=current_user.id,
        )

        db.add(target)
        await db.commit()
        await db.refresh(target)

        logger.info(f"Created inspection target: {target.id}")
        return target

    except Exception as e:
        logger.error(f"Failed to create inspection target: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/targets/{target_id}",
    response_model=InspectionTargetResponse,
    tags=["inspection-masters"],
)
async def get_inspection_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査対象を取得"""
    try:
        target = await db.execute(
            select(InspectionTarget)
            .options(selectinload(InspectionTarget.inspection_items))
            .where(InspectionTarget.id == target_id)
        )
        target = target.scalar_one_or_none()

        if not target:
            raise HTTPException(status_code=404, detail="Inspection target not found")

        return target

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inspection target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/targets",
    response_model=PaginatedResponse[InspectionTargetResponse],
    tags=["inspection-masters"],
)
async def list_inspection_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査対象一覧を取得"""
    try:
        # ベースクエリ
        query = select(InspectionTarget)
        count_query = select(func.count(InspectionTarget.id))

        # 検索条件
        if search:
            search_filter = or_(
                InspectionTarget.name.ilike(f"%{search}%"),
                InspectionTarget.product_code.ilike(f"%{search}%"),
                InspectionTarget.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # 総件数取得
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # ページング
        offset = (page - 1) * page_size
        query = (
            query.offset(offset)
            .limit(page_size)
            .order_by(InspectionTarget.created_at.desc())
        )

        # データ取得
        result = await db.execute(query)
        targets = result.scalars().all()

        return PaginatedResponse(
            items=targets,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list inspection targets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/targets/{target_id}",
    response_model=InspectionTargetResponse,
    tags=["inspection-masters"],
)
async def update_inspection_target(
    target_id: uuid.UUID,
    target_data: InspectionTargetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査対象を更新"""
    try:
        target = await db.execute(
            select(InspectionTarget).where(InspectionTarget.id == target_id)
        )
        target = target.scalar_one_or_none()

        if not target:
            raise HTTPException(status_code=404, detail="Inspection target not found")

        # 重複チェック（自分以外）
        if target_data.product_code and target_data.product_code != target.product_code:
            existing = await db.execute(
                select(InspectionTarget).where(
                    and_(
                        InspectionTarget.product_code == target_data.product_code,
                        InspectionTarget.id != target_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=400, detail="Product code already exists"
                )

        # 更新
        for field, value in target_data.dict(exclude_unset=True).items():
            if hasattr(target, field):
                setattr(target, field, value)

        await db.commit()
        await db.refresh(target)

        logger.info(f"Updated inspection target: {target.id}")
        return target

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update inspection target: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/targets/{target_id}", status_code=204, tags=["inspection-masters"])
async def delete_inspection_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査対象を削除"""
    try:
        target = await db.execute(
            select(InspectionTarget).where(InspectionTarget.id == target_id)
        )
        target = target.scalar_one_or_none()

        if not target:
            raise HTTPException(status_code=404, detail="Inspection target not found")

        await db.delete(target)
        await db.commit()

        logger.info(f"Deleted inspection target: {target_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete inspection target: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# 検査項目管理API


@router.post(
    "/items", response_model=InspectionItemResponse, tags=["inspection-masters"]
)
async def create_inspection_item(
    item_data: InspectionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目を作成"""
    try:
        # 検査対象存在チェック
        target = await db.execute(
            select(InspectionTarget).where(InspectionTarget.id == item_data.target_id)
        )
        if not target.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Inspection target not found")

        # 検査基準存在チェック
        if item_data.criteria_id:
            criteria = await db.execute(
                select(InspectionCriteria).where(
                    InspectionCriteria.id == item_data.criteria_id
                )
            )
            if not criteria.scalar_one_or_none():
                raise HTTPException(
                    status_code=400, detail="Inspection criteria not found"
                )

        item = InspectionItem(
            target_id=item_data.target_id,
            name=item_data.name,
            description=item_data.description,
            type=item_data.type,
            pipeline_id=item_data.pipeline_id,
            pipeline_params=item_data.pipeline_params or {},
            execution_order=item_data.execution_order,
            is_required=item_data.is_required,
            criteria_id=item_data.criteria_id,
            created_by=current_user.id,
        )

        db.add(item)
        await db.commit()
        await db.refresh(item)

        logger.info(f"Created inspection item: {item.id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create inspection item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/items/{item_id}",
    response_model=InspectionItemResponse,
    tags=["inspection-masters"],
)
async def get_inspection_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目を取得"""
    try:
        item = await db.execute(
            select(InspectionItem)
            .options(
                selectinload(InspectionItem.target),
                selectinload(InspectionItem.criteria),
            )
            .where(InspectionItem.id == item_id)
        )
        item = item.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Inspection item not found")

        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inspection item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/targets/{target_id}/items",
    response_model=PaginatedResponse[InspectionItemResponse],
    tags=["inspection-masters"],
)
async def list_inspection_items(
    target_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目一覧を取得"""
    try:
        # ベースクエリ
        query = select(InspectionItem).where(InspectionItem.target_id == target_id)
        count_query = select(func.count(InspectionItem.id)).where(
            InspectionItem.target_id == target_id
        )

        # 総件数取得
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # ページング
        offset = (page - 1) * page_size
        query = (
            query.offset(offset)
            .limit(page_size)
            .order_by(InspectionItem.execution_order.asc())
        )

        # データ取得
        result = await db.execute(query)
        items = result.scalars().all()

        return PaginatedResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list inspection items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 検査基準管理API


@router.post(
    "/criterias", response_model=InspectionCriteriaResponse, tags=["inspection-masters"]
)
async def create_inspection_criteria(
    criteria_data: InspectionCriteriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査基準を作成"""
    try:
        criteria = InspectionCriteria(
            name=criteria_data.name,
            description=criteria_data.description,
            judgment_type=criteria_data.judgment_type,
            spec=criteria_data.spec,
            created_by=current_user.id,
        )

        db.add(criteria)
        await db.commit()
        await db.refresh(criteria)

        logger.info(f"Created inspection criteria: {criteria.id}")
        return criteria

    except Exception as e:
        logger.error(f"Failed to create inspection criteria: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/criterias",
    response_model=PaginatedResponse[InspectionCriteriaResponse],
    tags=["inspection-masters"],
)
async def list_inspection_criterias(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査基準一覧を取得"""
    try:
        # ベースクエリ
        query = select(InspectionCriteria)
        count_query = select(func.count(InspectionCriteria.id))

        # 検索条件
        if search:
            search_filter = or_(
                InspectionCriteria.name.ilike(f"%{search}%"),
                InspectionCriteria.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # 総件数取得
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # ページング
        offset = (page - 1) * page_size
        query = (
            query.offset(offset)
            .limit(page_size)
            .order_by(InspectionCriteria.created_at.desc())
        )

        # データ取得
        result = await db.execute(query)
        criterias = result.scalars().all()

        return PaginatedResponse(
            items=criterias,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list inspection criterias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

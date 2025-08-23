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
from app.models.inspection import (
    InspectionTarget,
    InspectionItem,
    InspectionCriteria,
    ProductTypeGroup,
    ProductTypeGroupMember,
    ProductCodeName,
)
from app.models.product import ProductMaster
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
    ProductTypeGroupCreate,
    ProductTypeGroupUpdate,
    ProductTypeGroupResponse,
    ProductTypeGroupMemberCreate,
    ProductTypeGroupMemberResponse,
    ProcessMasterCreate,
    ProcessMasterUpdate,
    ProcessMasterResponse,
    ProductCodeNameCreate,
    ProductCodeNameUpdate,
    ProductCodeNameResponse,
)
from app.services.auth_service import get_current_user


def _extract_user_id(current_user) -> Optional[uuid.UUID]:
    try:
        if isinstance(current_user, dict):
            val = current_user.get("id")
            return uuid.UUID(val) if isinstance(val, str) else val
        # object with attribute
        val = getattr(current_user, "id", None)
        return uuid.UUID(val) if isinstance(val, str) else val
    except Exception:
        return None

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
    """検査対象を作成（vNEXT: group_id + process_code 必須）"""
    try:
        if not target_data.group_id or not target_data.process_code:
            raise HTTPException(status_code=400, detail="group_id and process_code are required")

        # 一意性: group_id + process_code + version
        dup = await db.execute(
            select(InspectionTarget).where(
                and_(
                    InspectionTarget.group_id == target_data.group_id,
                    InspectionTarget.process_code == target_data.process_code,
                    InspectionTarget.version == target_data.version,
                )
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Target already exists for group+process+version")

        target = InspectionTarget(
            name=target_data.name,
            description=target_data.description,
            product_name=target_data.product_name,
            group_id=target_data.group_id,
            group_name=target_data.group_name,
            process_code=target_data.process_code,
            version=target_data.version,
            metadata_=target_data.metadata or {},
            created_by=_extract_user_id(current_user),
        )

        db.add(target)
        await db.commit()
        await db.refresh(target)

        logger.info(f"Created inspection target: {target.id}")
        return target

    except HTTPException as e:
        # Preserve intended HTTP error codes (e.g., 400 on duplicate)
        await db.rollback()
        logger.error(f"Failed to create inspection target (client error): {e.detail}")
        raise
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

        # 検索条件（group+process+name ベース）
        if search:
            like = f"%{search}%"
            # join: 型式グループの group_code/name も対象にする
            query = query.join(
                ProductTypeGroup,
                InspectionTarget.group_id == ProductTypeGroup.id,
                isouter=True,
            )
            count_query = count_query.join(
                ProductTypeGroup,
                InspectionTarget.group_id == ProductTypeGroup.id,
                isouter=True,
            )

            search_filter = or_(
                InspectionTarget.name.ilike(like),
                InspectionTarget.description.ilike(like),
                InspectionTarget.group_name.ilike(like),
                InspectionTarget.process_code.ilike(like),
                ProductTypeGroup.group_code.ilike(like),
                ProductTypeGroup.name.ilike(like),
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

        # 重複チェック（group+process+version）
        if (target_data.group_id is not None) or (target_data.process_code is not None) or (target_data.version is not None):
            gid = target_data.group_id or target.group_id
            pcd = target_data.process_code or target.process_code
            ver = target_data.version or target.version
            dup = await db.execute(
                select(InspectionTarget).where(
                    and_(
                        InspectionTarget.group_id == gid,
                        InspectionTarget.process_code == pcd,
                        InspectionTarget.version == ver,
                        InspectionTarget.id != target_id,
                    )
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Target already exists for group+process+version")

        # 更新
        for field, value in target_data.dict(exclude_unset=True).items():
            if field == "metadata":
                setattr(target, "metadata_", value)
                continue
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
            created_by=_extract_user_id(current_user),
        )

        db.add(item)
        await db.commit()
        # Re-query with eager loads to avoid async lazy-loading at response time
        item = (
            await db.execute(
                select(InspectionItem)
                .options(
                    selectinload(InspectionItem.target),
                    selectinload(InspectionItem.criteria),
                )
                .where(InspectionItem.id == item.id)
            )
        ).scalar_one()

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


@router.put(
    "/items/{item_id}",
    response_model=InspectionItemResponse,
    tags=["inspection-masters"],
)
async def update_inspection_item(
    item_id: uuid.UUID,
    item_data: InspectionItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目を更新"""
    try:
        result = await db.execute(
            select(InspectionItem).where(InspectionItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Inspection item not found")

        for field, value in item_data.dict(exclude_unset=True).items():
            if hasattr(item, field):
                setattr(item, field, value)

        await db.commit()
        # Re-query with eager loads to avoid MissingGreenlet on response serialization
        item = (
            await db.execute(
                select(InspectionItem)
                .options(
                    selectinload(InspectionItem.target),
                    selectinload(InspectionItem.criteria),
                )
                .where(InspectionItem.id == item_id)
            )
        ).scalar_one_or_none()
        return item
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update inspection item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}", status_code=204, tags=["inspection-masters"])
async def delete_inspection_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """検査項目を削除"""
    try:
        result = await db.execute(
            select(InspectionItem).where(InspectionItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Inspection item not found")
        await db.delete(item)
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete inspection item: {e}")
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

        # データ取得（関連をselectinloadで先読みしてレスポンス時の遅延ロードを回避）
        result = await db.execute(
            query.options(
                selectinload(InspectionItem.target),
                selectinload(InspectionItem.criteria),
            )
        )
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


@router.get(
    "/products/{product_id}/items",
    response_model=PaginatedResponse[InspectionItemResponse],
    tags=["inspection-masters"],
)
async def list_items_by_product(
    product_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """製品IDから検査項目一覧を取得

    設計上の前提:
    - Webアプリで作成される InspectionTarget.product_code は製品の型式コード(ProductMaster.product_code)と一致させる
    - 上記が見つからない場合のフォールバックとして、work_order_id などの補助キーも試行
    """
    try:
        # 製品取得（UUID or 生成IDの両対応は products API と同等のロジックにするのが理想だが、ここでは単純化）
        from uuid import UUID

        product: ProductMaster | None = None
        try:
            uid = UUID(product_id)
            res = await db.execute(select(ProductMaster).where(ProductMaster.id == uid))
            product = res.scalar_one_or_none()
        except Exception:
            # 非UUIDは全件からの簡易探索にフォールバック
            rows = (await db.execute(select(ProductMaster))).scalars().all()
            for r in rows:
                # 生成ID（work_order_id_instruction_id_machine_monthlySequence）形式の簡易一致
                gen = f"{r.work_order_id}_{r.instruction_id}_{r.machine_number}_{r.monthly_sequence}"
                if gen == product_id:
                    product = r
                    break

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # 1) 型式グループ優先: product.product_code が所属するグループを検索
        group = None
        grp = await db.execute(
            select(ProductTypeGroup)
            .join(ProductTypeGroupMember)
            .where(ProductTypeGroupMember.product_code == product.product_code)
        )
        group = grp.scalar_one_or_none()

        target = None
        if group:
            tgt_by_group = await db.execute(
                select(InspectionTarget).where(InspectionTarget.group_id == group.id)
            )
            target = tgt_by_group.scalar_one_or_none()

        # 2) グループ未設定の場合は従来の product_code マッピング
        if not target:
            # まず product_code
            target_q = select(InspectionTarget).where(
                InspectionTarget.product_code == product.product_code
            )
            target = (await db.execute(target_q)).scalar_one_or_none()
        if not target:
            # フォールバック: work_order_id
            alt_q = select(InspectionTarget).where(
                InspectionTarget.product_code == product.work_order_id
            )
            target = (await db.execute(alt_q)).scalar_one_or_none()

        if not target:
            # 一致する検査対象がない場合は空で返す（404ではなく空配列の方がクライアント実装簡素）
            return PaginatedResponse(
                items=[], total_count=0, page=page, page_size=page_size, total_pages=0
            )

        # 対象に紐づく項目を順序で返す
        base_q = select(InspectionItem).where(InspectionItem.target_id == target.id)
        count_q = select(func.count(InspectionItem.id)).where(
            InspectionItem.target_id == target.id
        )

        total_count = (await db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        rows = (
            (
                await db.execute(
                    base_q.options(
                        selectinload(InspectionItem.target),
                        selectinload(InspectionItem.criteria),
                    )
                    .order_by(InspectionItem.execution_order.asc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        return PaginatedResponse(
            items=rows,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list items by product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 型式グループ管理API


@router.post(
    "/type-groups", response_model=ProductTypeGroupResponse, tags=["inspection-masters"]
)
async def create_product_code_group(
    payload: ProductTypeGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = ProductTypeGroup(
            name=payload.name,
            description=payload.description,
            group_code=payload.group_code,
            created_by=_extract_user_id(current_user),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create Product Code group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/type-groups",
    response_model=PaginatedResponse[ProductTypeGroupResponse],
    tags=["inspection-masters"],
)
async def list_product_code_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        count = (
            await db.execute(select(func.count(ProductTypeGroup.id)))
        ).scalar() or 0
        offset = (page - 1) * page_size
        rows = (
            (
                await db.execute(
                    select(ProductTypeGroup)
                    .order_by(ProductTypeGroup.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return PaginatedResponse(
            items=rows,
            total_count=count,
            page=page,
            page_size=page_size,
            total_pages=(count + page_size - 1) // page_size,
        )
    except Exception as e:
        logger.error(f"Failed to list Product Code groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/type-groups/{group_id}",
    response_model=ProductTypeGroupResponse,
    tags=["inspection-masters"],
)
async def update_product_code_group(
    group_id: uuid.UUID,
    payload: ProductTypeGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(
                select(ProductTypeGroup).where(ProductTypeGroup.id == group_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Group not found")
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit()
        await db.refresh(row)
        return row
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update Product Code group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/type-groups/{group_id}", status_code=204, tags=["inspection-masters"])
async def delete_product_code_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(
                select(ProductTypeGroup).where(ProductTypeGroup.id == group_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.delete(row)
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete Product Code group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/type-groups/{group_id}/members",
    response_model=ProductTypeGroupMemberResponse,
    tags=["inspection-masters"],
)
async def add_group_member(
    group_id: uuid.UUID,
    payload: ProductTypeGroupMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        grp = (
            await db.execute(
                select(ProductTypeGroup).where(ProductTypeGroup.id == group_id)
            )
        ).scalar_one_or_none()
        if not grp:
            raise HTTPException(status_code=404, detail="Group not found")
        member = ProductTypeGroupMember(
            group_id=group_id, product_code=payload.product_code
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add group member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/type-groups/{group_id}/members",
    response_model=List[ProductTypeGroupMemberResponse],
    tags=["inspection-masters"],
)
async def list_group_members(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        rows = (
            (
                await db.execute(
                    select(ProductTypeGroupMember)
                    .where(ProductTypeGroupMember.group_id == group_id)
                    .order_by(ProductTypeGroupMember.product_code.asc())
                )
            )
            .scalars()
            .all()
        )
        return rows
    except Exception as e:
        logger.error(f"Failed to list group members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/type-groups/{group_id}/members/{product_code}",
    status_code=204,
    tags=["inspection-masters"],
)
async def delete_group_member(
    group_id: uuid.UUID,
    product_code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(
                select(ProductTypeGroupMember).where(
                    and_(
                        ProductTypeGroupMember.group_id == group_id,
                        ProductTypeGroupMember.product_code == product_code,
                    )
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.delete(row)
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete group member: {e}")
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
        # Normalize enum and pydantic model to serializable primitives
        jt = (
            criteria_data.judgment_type.value
            if hasattr(criteria_data.judgment_type, "value")
            else str(criteria_data.judgment_type)
        )
        try:
            spec_dict = (
                criteria_data.spec.model_dump()  # Pydantic v2
                if hasattr(criteria_data.spec, "model_dump")
                else criteria_data.spec.dict()  # Pydantic v1 fallback
            )
        except Exception:
            # If already a plain dict
            spec_dict = criteria_data.spec  # type: ignore

        criteria = InspectionCriteria(
            name=criteria_data.name,
            description=criteria_data.description,
            judgment_type=jt,
            spec=spec_dict,
            created_by=_extract_user_id(current_user),
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


@router.get(
    "/criterias/{criteria_id}", response_model=InspectionCriteriaResponse, tags=["inspection-masters"]
)
async def get_inspection_criteria(
    criteria_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(select(InspectionCriteria).where(InspectionCriteria.id == criteria_id))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Inspection criteria not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inspection criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/criterias/{criteria_id}", response_model=InspectionCriteriaResponse, tags=["inspection-masters"]
)
async def update_inspection_criteria(
    criteria_id: uuid.UUID,
    payload: InspectionCriteriaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(select(InspectionCriteria).where(InspectionCriteria.id == criteria_id))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Inspection criteria not found")
        # Apply updates with proper normalization
        data = payload.dict(exclude_unset=True)
        if "judgment_type" in data and data["judgment_type"] is not None:
            jt = data["judgment_type"]
            data["judgment_type"] = jt.value if hasattr(jt, "value") else str(jt)
        if "spec" in data and data["spec"] is not None:
            spec = data["spec"]
            try:
                data["spec"] = (
                    spec.model_dump() if hasattr(spec, "model_dump") else spec.dict()
                )
            except Exception:
                # assume already plain dict
                pass
        for field, value in data.items():
            if hasattr(row, field):
                setattr(row, field, value)
        await db.commit()
        await db.refresh(row)
        return row
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update inspection criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/criterias/{criteria_id}", status_code=204, tags=["inspection-masters"]
)
async def delete_inspection_criteria(
    criteria_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(select(InspectionCriteria).where(InspectionCriteria.id == criteria_id))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Inspection criteria not found")
        await db.delete(row)
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete inspection criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# products + process_code から検査項目を取得（厳格運用: 型式グループ未所属は返さない）
@router.get(
    "/products/{product_id}/processes/{process_code}/items",
    response_model=PaginatedResponse[InspectionItemResponse],
    tags=["inspection-masters"],
)
async def list_items_by_product_and_process(
    product_id: str,
    process_code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        from uuid import UUID
        product: ProductMaster | None = None
        try:
            uid = UUID(product_id)
            res = await db.execute(select(ProductMaster).where(ProductMaster.id == uid))
            product = res.scalar_one_or_none()
        except Exception:
            rows = (await db.execute(select(ProductMaster))).scalars().all()
            for r in rows:
                gen = f"{r.work_order_id}_{r.instruction_id}_{r.machine_number}_{r.monthly_sequence}"
                if gen == product_id:
                    product = r
                    break

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # 厳格運用: 型式グループに属していない場合は空を返す
        grp = await db.execute(
            select(ProductTypeGroup)
            .join(ProductTypeGroupMember)
            .where(ProductTypeGroupMember.product_code == product.product_code)
        )
        group = grp.scalar_one_or_none()
        if not group:
            return PaginatedResponse(
                items=[], total_count=0, page=page, page_size=page_size, total_pages=0
            )

        # 型式グループ + 工程コード一致のターゲットのみ
        q = await db.execute(
            select(InspectionTarget)
            .where(
                and_(
                    InspectionTarget.group_id == group.id,
                    InspectionTarget.process_code == process_code,
                )
            )
            .order_by(InspectionTarget.created_at.desc())
        )
        target = q.scalar_one_or_none()

        if not target:
            return PaginatedResponse(
                items=[], total_count=0, page=page, page_size=page_size, total_pages=0
            )

        base_q = select(InspectionItem).where(InspectionItem.target_id == target.id)
        count_q = select(func.count(InspectionItem.id)).where(
            InspectionItem.target_id == target.id
        )
        total_count = (await db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        rows = (
            (
                await db.execute(
                    base_q.options(
                        selectinload(InspectionItem.target),
                        selectinload(InspectionItem.criteria),
                    )
                    .order_by(InspectionItem.execution_order.asc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        return PaginatedResponse(
            items=rows,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list items by product+process: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# 工程マスタ API（最小: 一覧のみ）
@router.post(
    "/processes",
    response_model=ProcessMasterResponse,
    tags=["inspection-masters"],
)
async def create_process(
    payload: ProcessMasterCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.inspection import ProcessMaster
    try:
        exists = (
            await db.execute(select(ProcessMaster).where(ProcessMaster.process_code == payload.process_code))
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=400, detail="Process code already exists")
        row = ProcessMaster(process_code=payload.process_code, process_name=payload.process_name)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row
    except HTTPException:
        await db.rollback(); raise
    except Exception as e:
        await db.rollback(); logger.error(f"Failed to create process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/processes",
    response_model=PaginatedResponse[ProcessMasterResponse],
    tags=["inspection-masters"],
)
async def list_processes(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.inspection import ProcessMaster
    try:
        total = (await db.execute(select(func.count(ProcessMaster.id)))).scalar() or 0
        offset = (page - 1) * page_size
        rows = (
            (await db.execute(
                select(ProcessMaster)
                .order_by(ProcessMaster.process_code.asc())
                .offset(offset)
                .limit(page_size)
            ))
            .scalars()
            .all()
        )
        return PaginatedResponse(
            items=rows,
            total_count=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
    except Exception as e:
        logger.error(f"Failed to list processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/processes/{process_code}",
    response_model=ProcessMasterResponse,
    tags=["inspection-masters"],
)
async def get_process(
    process_code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.inspection import ProcessMaster
    row = (
        await db.execute(select(ProcessMaster).where(ProcessMaster.process_code == process_code))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Process not found")
    return row

@router.put(
    "/processes/{process_code}",
    response_model=ProcessMasterResponse,
    tags=["inspection-masters"],
)
async def update_process(
    process_code: str,
    payload: ProcessMasterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.inspection import ProcessMaster
    try:
        row = (
            await db.execute(select(ProcessMaster).where(ProcessMaster.process_code == process_code))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Process not found")
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit(); await db.refresh(row)
        return row
    except HTTPException:
        await db.rollback(); raise
    except Exception as e:
        await db.rollback(); logger.error(f"Failed to update process: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 型式コード・型式名マスタ API


@router.post(
    "/type-names",
    response_model=ProductCodeNameResponse,
    tags=["inspection-masters"],
)
async def create_product_code_name(
    payload: ProductCodeNameCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        exists = (
            await db.execute(
                select(ProductCodeName).where(ProductCodeName.product_code == payload.product_code)
            )
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=400, detail="Product code already exists")
        row = ProductCodeName(product_code=payload.product_code, product_name=payload.product_name)
        db.add(row); await db.commit(); await db.refresh(row)
        return row
    except HTTPException:
        await db.rollback(); raise
    except Exception as e:
        await db.rollback(); logger.error(f"Failed to create product code name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/type-names",
    response_model=PaginatedResponse[ProductCodeNameResponse],
    tags=["inspection-masters"],
)
async def list_product_code_names(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        base = select(ProductCodeName)
        if q:
            like = f"%{q}%"
            base = base.where(
                or_(
                    ProductCodeName.product_code.ilike(like),
                    ProductCodeName.product_name.ilike(like),
                )
            )
        total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        offset = (page - 1) * page_size
        rows = (
            (await db.execute(
                base.order_by(ProductCodeName.product_code.asc()).offset(offset).limit(page_size)
            ))
            .scalars()
            .all()
        )
        return PaginatedResponse(
            items=rows, total_count=total, page=page, page_size=page_size, total_pages=(total + page_size - 1)//page_size
        )
    except Exception as e:
        logger.error(f"Failed to list product code names: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/type-names/batch",
    response_model=List[ProductCodeNameResponse],
    tags=["inspection-masters"],
)
async def get_product_code_names_batch(
    codes: str = Query(..., description="comma separated product codes"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    wanted = [c.strip() for c in codes.split(',') if c.strip()]
    if not wanted:
        return []
    rows = (await db.execute(select(ProductCodeName))).scalars().all()
    out = [r for r in rows if r.product_code in wanted]
    return out


@router.put(
    "/type-names/{product_code}",
    response_model=ProductCodeNameResponse,
    tags=["inspection-masters"],
)
async def update_product_code_name(
    product_code: str,
    payload: ProductCodeNameUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = (
            await db.execute(select(ProductCodeName).where(ProductCodeName.product_code == product_code))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Product code not found")
        if payload.product_name is not None:
            row.product_name = payload.product_name
        await db.commit(); await db.refresh(row)
        return row
    except HTTPException:
        await db.rollback(); raise
    except Exception as e:
        await db.rollback(); logger.error(f"Failed to update product code name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/processes/{process_code}",
    status_code=204,
    tags=["inspection-masters"],
)
async def delete_process(
    process_code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.inspection import ProcessMaster
    try:
        row = (
            await db.execute(select(ProcessMaster).where(ProcessMaster.process_code == process_code))
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Process not found")
        await db.delete(row); await db.commit(); return None
    except HTTPException:
        await db.rollback(); raise
    except Exception as e:
        await db.rollback(); logger.error(f"Failed to delete process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

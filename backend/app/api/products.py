from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.product import (
    ProductInfo,
    ProductSearchResponse,
    ProductSuggestion,
    ProductSyncResponse,
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    SyncStatus,
)
from app.models.product import ProductMaster
from app.database import get_db

router = APIRouter()


def _to_schema(p: ProductMaster) -> ProductInfo:
    return ProductInfo(
        id=str(p.id),
        workOrderId=p.work_order_id,
        instructionId=p.instruction_id,
        productType=p.product_type,
        machineNumber=p.machine_number,
        productionDate=(
            p.production_date.isoformat()
            if isinstance(p.production_date, (date, datetime))
            else str(p.production_date)
        ),
        monthlySequence=p.monthly_sequence,
        qrRawData=p.qr_raw_data,
        status=p.status,
        createdAt=int(p.created_at.timestamp() * 1000) if p.created_at else None,
        updatedAt=int(p.updated_at.timestamp() * 1000) if p.updated_at else None,
        lastAccessedAt=(
            int(p.last_accessed_at.timestamp() * 1000) if p.last_accessed_at else None
        ),
        accessCount=p.access_count or 0,
        isCached=p.is_cached,
        serverSyncStatus=p.server_sync_status,
    )


def _apply_update(p: ProductMaster, upd: ProductUpdate) -> None:
    if upd.product_type is not None:
        p.product_type = upd.product_type
    if upd.machine_number is not None:
        p.machine_number = upd.machine_number
    if upd.production_date is not None:
        try:
            p.production_date = datetime.fromisoformat(upd.production_date).date()
        except Exception:
            p.production_date = p.production_date
    if upd.monthly_sequence is not None:
        p.monthly_sequence = upd.monthly_sequence
    if upd.qr_raw_data is not None:
        p.qr_raw_data = upd.qr_raw_data
    if upd.status is not None:
        p.status = upd.status.value if hasattr(upd.status, "value") else str(upd.status)
    if upd.is_cached is not None:
        p.is_cached = upd.is_cached
    if upd.server_sync_status is not None:
        p.server_sync_status = (
            upd.server_sync_status.value
            if hasattr(upd.server_sync_status, "value")
            else str(upd.server_sync_status)
        )


@router.get("/products/{product_id}", response_model=ProductInfo)
async def get_product_info(
    product_id: str, db: AsyncSession = Depends(get_db)
) -> ProductInfo:
    from uuid import UUID

    row = None
    try:
        uid = UUID(product_id)
        res = await db.execute(select(ProductMaster).where(ProductMaster.id == uid))
        row = res.scalar_one_or_none()
    except Exception:
        # Not a valid UUID; attempt alternative lookup by composite key encoded id
        # Expecting format: WORK_INST_MACHINE_SEQ
        parts = product_id.split("_")
        if len(parts) >= 4:
            work, inst, machine, seq = parts[0], parts[1], parts[2], parts[3]
            try:
                res = await db.execute(
                    select(ProductMaster).where(
                        ProductMaster.work_order_id == work,
                        ProductMaster.instruction_id == inst,
                        ProductMaster.machine_number == machine,
                        ProductMaster.monthly_sequence == int(seq),
                    )
                )
                row = res.scalar_one_or_none()
            except Exception:
                pass
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    # update access info
    row.access_count = (row.access_count or 0) + 1
    row.last_accessed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return _to_schema(row)


@router.get("/products/search", response_model=ProductSearchResponse)
async def search_products(
    work_order_id: Optional[str] = Query(None),
    instruction_id: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    machine_number: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    import logging

    print(f"=== SEARCH ENDPOINT CALLED ===")
    print(f"work_order_id: {work_order_id}")
    print(f"instruction_id: {instruction_id}")
    print(f"product_type: {product_type}")

    logger = logging.getLogger(__name__)

    try:
        logger.info(
            f"Search request - work_order_id: {work_order_id}, instruction_id: {instruction_id}, product_type: {product_type}"
        )

        stmt = select(ProductMaster)
        if work_order_id:
            stmt = stmt.where(ProductMaster.work_order_id == work_order_id)
        if instruction_id:
            stmt = stmt.where(ProductMaster.instruction_id == instruction_id)
        if product_type:
            stmt = stmt.where(ProductMaster.product_type.ilike(f"%{product_type}%"))
        if machine_number:
            # allow partial match for machine number to improve usability
            stmt = stmt.where(ProductMaster.machine_number.ilike(f"%{machine_number}%"))
        if start_date:
            try:
                sd = datetime.fromisoformat(start_date).date()
                stmt = stmt.where(ProductMaster.production_date >= sd)
            except Exception:
                pass
        if end_date:
            try:
                ed = datetime.fromisoformat(end_date).date()
                stmt = stmt.where(ProductMaster.production_date <= ed)
            except Exception:
                pass
        # Order by production order (latest first): production_date desc, monthly_sequence desc
        stmt = stmt.order_by(
            ProductMaster.production_date.desc(), ProductMaster.monthly_sequence.desc()
        )

        # Count total first
        total = (await db.execute(stmt.with_only_columns(func.count()))).scalar() or 0
        logger.info(f"Total count query result: {total}")

        # Get actual rows
        stmt = stmt.limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        logger.info(f"Retrieved {len(rows)} rows from database")

        # Convert to schema
        products = []
        for i, r in enumerate(rows):
            try:
                product = _to_schema(r)
                products.append(product)
                logger.info(f"Successfully converted row {i}: {r.work_order_id}")
            except Exception as e:
                logger.error(f"Error converting row {i} ({r.work_order_id}): {e}")
                raise

        result = ProductSearchResponse(
            products=products,
            totalCount=total,
            hasMore=total > len(products),
            nextPageToken=None,
        )
        logger.info(f"Returning response with {len(products)} products")
        return result

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/products/by-qr", response_model=ProductInfo)
async def get_product_by_qr(
    data: str = Query(..., description="raw QR data"),
    db: AsyncSession = Depends(get_db),
) -> ProductInfo:
    # Simple heuristic: try to find a work_order_id embedded in the data
    # This should be replaced with a proper QR parser aligned with docs
    candidates = (await db.execute(select(ProductMaster))).scalars().all()
    for r in candidates:
        if r.work_order_id in data or r.instruction_id in data or str(r.id) in data:
            return _to_schema(r)
    raise HTTPException(status_code=404, detail="Product not found for QR data")


@router.get("/products/suggestions", response_model=List[ProductSuggestion])
async def get_suggestions(
    q: str = Query(""), db: AsyncSession = Depends(get_db)
) -> List[ProductSuggestion]:
    stmt = select(ProductMaster).limit(50)
    rows = (await db.execute(stmt)).scalars().all()
    out: List[ProductSuggestion] = []
    ql = q.lower()
    for r in rows:
        if not q or (ql in r.product_type.lower()) or (q in r.work_order_id):
            out.append(
                ProductSuggestion(
                    productId=str(r.id),
                    displayText=f"{r.product_type} - {r.machine_number}",
                    productType=r.product_type,
                    machineNumber=r.machine_number,
                    relevanceScore=0.9,
                )
            )
    return out[:10]


@router.get("/products", response_model=List[ProductInfo])
async def list_products(
    product_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
) -> List[ProductInfo]:
    stmt = select(ProductMaster)
    if product_type:
        stmt = stmt.where(ProductMaster.product_type.ilike(f"%{product_type}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_schema(r) for r in rows]


@router.get("/products:batch", response_model=List[ProductInfo])
async def get_products_batch(
    ids: str = Query(..., description="comma separated IDs"),
    db: AsyncSession = Depends(get_db),
) -> List[ProductInfo]:
    wanted = [i.strip() for i in ids.split(",") if i.strip()]
    if not wanted:
        return []
    # cast to text compare for portability
    rows = (await db.execute(select(ProductMaster))).scalars().all()
    pick = [r for r in rows if str(r.id) in wanted]
    return [_to_schema(r) for r in pick]


@router.get("/products/sync", response_model=ProductSyncResponse)
async def sync_products(
    last_sync: int = Query(0), db: AsyncSession = Depends(get_db)
) -> ProductSyncResponse:
    rows = (await db.execute(select(ProductMaster))).scalars().all()
    updates = [_to_schema(r) for r in rows]
    now = int(datetime.utcnow().timestamp() * 1000)
    return ProductSyncResponse(
        updates=updates,
        deletions=[],
        syncTimestamp=now,
        totalUpdated=len(updates),
        totalDeleted=0,
    )


# Admin: create product
@router.post("/products", response_model=ProductInfo)
async def create_product(
    payload: ProductCreate, db: AsyncSession = Depends(get_db)
) -> ProductInfo:
    try:
        prod_date = datetime.fromisoformat(payload.production_date).date()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid productionDate format (expected ISO-8601 YYYY-MM-DD)",
        )

    # Check unique composite key
    exists_stmt = select(ProductMaster).where(
        ProductMaster.work_order_id == payload.work_order_id,
        ProductMaster.instruction_id == payload.instruction_id,
        ProductMaster.machine_number == payload.machine_number,
        ProductMaster.monthly_sequence == payload.monthly_sequence,
    )
    if (await db.execute(exists_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Product with same key already exists"
        )

    row = ProductMaster(
        work_order_id=payload.work_order_id,
        instruction_id=payload.instruction_id,
        product_type=payload.product_type,
        machine_number=payload.machine_number,
        production_date=prod_date,
        monthly_sequence=payload.monthly_sequence,
        qr_raw_data=payload.qr_raw_data,
        status=(
            payload.status.value
            if hasattr(payload.status, "value")
            else str(payload.status)
        ),
        is_cached=payload.is_cached,
        server_sync_status=(
            payload.server_sync_status.value
            if hasattr(payload.server_sync_status, "value")
            else str(payload.server_sync_status)
        ),
        access_count=0,
        last_accessed_at=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_schema(row)


# Admin: update product
@router.put("/products/{product_id}", response_model=ProductInfo)
async def update_product(
    product_id: str, payload: ProductUpdate, db: AsyncSession = Depends(get_db)
) -> ProductInfo:
    # Resolve row
    from uuid import UUID

    row = None
    try:
        uid = UUID(product_id)
        row = (
            await db.execute(select(ProductMaster).where(ProductMaster.id == uid))
        ).scalar_one_or_none()
    except Exception:
        parts = product_id.split("_")
        if len(parts) >= 4:
            work, inst, machine, seq = parts[0], parts[1], parts[2], parts[3]
            row = (
                await db.execute(
                    select(ProductMaster).where(
                        ProductMaster.work_order_id == work,
                        ProductMaster.instruction_id == inst,
                        ProductMaster.machine_number == machine,
                        ProductMaster.monthly_sequence == int(seq),
                    )
                )
            ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    _apply_update(row, payload)
    await db.commit()
    await db.refresh(row)
    return _to_schema(row)


# Admin: delete product
@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)) -> None:
    from uuid import UUID

    row = None
    try:
        uid = UUID(product_id)
        row = (
            await db.execute(select(ProductMaster).where(ProductMaster.id == uid))
        ).scalar_one_or_none()
    except Exception:
        parts = product_id.split("_")
        if len(parts) >= 4:
            work, inst, machine, seq = parts[0], parts[1], parts[2], parts[3]
            row = (
                await db.execute(
                    select(ProductMaster).where(
                        ProductMaster.work_order_id == work,
                        ProductMaster.instruction_id == inst,
                        ProductMaster.machine_number == machine,
                        ProductMaster.monthly_sequence == int(seq),
                    )
                )
            ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(row)
    await db.commit()
    return None


# Admin: seed demo data
@router.post("/products/seed", response_model=List[ProductInfo])
async def seed_products(db: AsyncSession = Depends(get_db)) -> List[ProductInfo]:
    demo = [
        dict(
            workOrderId="WORK-1001",
            instructionId="INST-01",
            productType="MODEL-A",
            machineNumber="MACHINE-001",
            productionDate="2025-08-01",
            monthlySequence=1,
        ),
        dict(
            workOrderId="WORK-1002",
            instructionId="INST-03",
            productType="MODEL-B",
            machineNumber="MACHINE-002",
            productionDate="2025-08-02",
            monthlySequence=12,
        ),
        dict(
            workOrderId="WORK-2001",
            instructionId="INST-02",
            productType="MODEL-C",
            machineNumber="MACHINE-010",
            productionDate="2025-08-10",
            monthlySequence=5,
        ),
    ]

    created = []
    for d in demo:
        try:
            payload = ProductCreate(**d)
            # reuse the creation logic
            try:
                prod_date = datetime.fromisoformat(payload.production_date).date()
            except Exception:
                continue
            exists_stmt = select(ProductMaster).where(
                ProductMaster.work_order_id == payload.work_order_id,
                ProductMaster.instruction_id == payload.instruction_id,
                ProductMaster.machine_number == payload.machine_number,
                ProductMaster.monthly_sequence == payload.monthly_sequence,
            )
            if (await db.execute(exists_stmt)).scalar_one_or_none():
                continue
            row = ProductMaster(
                work_order_id=payload.work_order_id,
                instruction_id=payload.instruction_id,
                product_type=payload.product_type,
                machine_number=payload.machine_number,
                production_date=prod_date,
                monthly_sequence=payload.monthly_sequence,
                status="ACTIVE",
                server_sync_status="SYNCED",
                is_cached=True,
                access_count=0,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            created.append(_to_schema(row))
        except Exception:
            continue
    await db.commit()
    return created

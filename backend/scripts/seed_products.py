import asyncio
from datetime import datetime
from app.database import init_db, AsyncSessionLocal
from app.models.product import ProductMaster
from sqlalchemy import select


DEMO = [
    dict(work_order_id="WORK-1001", instruction_id="INST-01", product_type="MODEL-A", machine_number="MACHINE-001", production_date="2025-08-01", monthly_sequence=1),
    dict(work_order_id="WORK-1002", instruction_id="INST-03", product_type="MODEL-B", machine_number="MACHINE-002", production_date="2025-08-02", monthly_sequence=12),
    dict(work_order_id="WORK-2001", instruction_id="INST-02", product_type="MODEL-C", machine_number="MACHINE-010", production_date="2025-08-10", monthly_sequence=5),
]


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        created = 0
        for d in DEMO:
            # check exists
            exists = await db.execute(
                select(ProductMaster).where(
                    ProductMaster.work_order_id == d["work_order_id"],
                    ProductMaster.instruction_id == d["instruction_id"],
                    ProductMaster.machine_number == d["machine_number"],
                    ProductMaster.monthly_sequence == d["monthly_sequence"],
                )
            )
            if exists.scalar_one_or_none():
                continue
            row = ProductMaster(
                work_order_id=d["work_order_id"],
                instruction_id=d["instruction_id"],
                product_type=d["product_type"],
                machine_number=d["machine_number"],
                production_date=datetime.fromisoformat(d["production_date"]).date(),
                monthly_sequence=d["monthly_sequence"],
                status="ACTIVE",
                is_cached=True,
                server_sync_status="SYNCED",
                access_count=0,
            )
            db.add(row)
            created += 1
        await db.commit()
        print(f"Seeded {created} products.")


if __name__ == "__main__":
    asyncio.run(main())


import os
import asyncio
import logging
from typing import Optional

import grpc
from grpc import aio as grpc_aio
from grpc_health.v1 import health_pb2, health_pb2_grpc

import sys
from pathlib import Path

gen_path = Path(__file__).resolve().parents[1] / "generated" / "python"
if str(gen_path) not in sys.path:
    sys.path.insert(0, str(gen_path))

from imageflow.v1 import evaluator_pb2, evaluator_pb2_grpc, ai_detection_pb2  # type: ignore

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inspection-evaluator")

Base = declarative_base()


class ProductTypeGroup(Base):
    __tablename__ = "product_code_groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    group_code = Column(String(100))


class ProductTypeGroupMember(Base):
    __tablename__ = "product_code_group_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey('product_code_groups.id'))
    product_code = Column(String(100))


class InspectionTarget(Base):
    __tablename__ = "inspection_targets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey('product_code_groups.id'))
    process_code = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class InspectionItem(Base):
    __tablename__ = "inspection_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), ForeignKey('inspection_targets.id'))
    pipeline_id = Column(UUID(as_uuid=True))
    is_required = Column(Boolean, default=True)
    criteria_id = Column(UUID(as_uuid=True), ForeignKey('inspection_criterias.id'))


class InspectionCriteria(Base):
    __tablename__ = "inspection_criterias"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_type = Column(String(50), nullable=False)
    spec = Column(JSON, nullable=False)


def create_session() -> sessionmaker:
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://imageflow:imageflow123@postgres:5432/imageflow")
    engine = create_async_engine(db_url, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class EvaluatorCore:
    def __init__(self, SessionFactory: sessionmaker):
        self.SessionFactory = SessionFactory

    async def resolve_criteria(self, product_code: str, process_code: str, pipeline_id: Optional[str]):
        if not (product_code and process_code and pipeline_id):
            return None
        try:
            pipeline_uuid = uuid.UUID(pipeline_id)
        except Exception:
            return None
        async with self.SessionFactory() as session:
            grp_row = (
                await session.execute(
                    select(ProductTypeGroupMember, ProductTypeGroup)
                    .join(ProductTypeGroup, ProductTypeGroupMember.group_id == ProductTypeGroup.id)
                    .where(ProductTypeGroupMember.product_code == product_code)
                )
            ).first()
            if not grp_row:
                return None
            group_id = grp_row[0].group_id

            tgt = (
                await session.execute(
                    select(InspectionTarget)
                    .where(
                        (InspectionTarget.group_id == group_id)
                        & (InspectionTarget.process_code == process_code)
                    )
                    .order_by(InspectionTarget.created_at.desc())
                )
            ).scalars().first()
            if not tgt:
                return None
            item = (
                await session.execute(
                    select(InspectionItem).where(
                        (InspectionItem.target_id == tgt.id)
                        & (InspectionItem.pipeline_id == pipeline_uuid)
                    )
                )
            ).scalars().first()
            if not item or not item.criteria_id:
                return None
            crit = (
                await session.execute(
                    select(InspectionCriteria).where(InspectionCriteria.id == item.criteria_id)
                )
            ).scalars().first()
            if not crit:
                return None
            return {
                "criteria_id": str(crit.id),
                "item_id": str(item.id),
                "judgment_type": crit.judgment_type,
                "spec": crit.spec,
            }

    def evaluate(self, detections, criteria: dict):
        det_count = len(detections)
        jt = (criteria.get("judgment_type") or "").upper()
        spec = criteria.get("spec") or {}

        def ok(val: bool) -> str:
            return "OK" if val else "NG"

        if jt == "BINARY":
            expected = spec.get("binary", {}).get("expected_value", True)
            return ok((det_count == 0) if expected else (det_count > 0)), {"detected": str(det_count)}
        if jt == "THRESHOLD":
            th = spec.get("threshold", {}).get("threshold")
            op = (spec.get("threshold", {}).get("operator") or "").upper()
            if th is None:
                return ok(det_count == 0), {"detected": str(det_count)}
            v = float(det_count)
            t = float(th)
            decision = {
                "LESS_THAN": v < t,
                "LESS_THAN_OR_EQUAL": v <= t,
                "GREATER_THAN": v > t,
                "GREATER_THAN_OR_EQUAL": v >= t,
                "EQUAL": v == t,
                "NOT_EQUAL": v != t,
            }.get(op, v <= t)
            return ok(decision), {"detected": str(det_count), "threshold": str(t), "operator": op}
        if jt == "CATEGORICAL":
            allowed = set(spec.get("categorical", {}).get("allowed_categories", []))
            all_allowed = all((d.class_name in allowed) for d in detections)
            return ok(all_allowed), {"allowed": ",".join(allowed), "detected": str(det_count)}
        if jt == "NUMERICAL":
            num = spec.get("numerical", {})
            v = float(det_count)
            mn = num.get("min_value")
            mx = num.get("max_value")
            ok_min = True if mn is None else v >= float(mn)
            ok_max = True if mx is None else v <= float(mx)
            return ok(ok_min and ok_max), {"detected": str(det_count), "min": str(mn or ""), "max": str(mx or "")}
        return ok(det_count == 0), {"detected": str(det_count)}


class InspectionEvaluatorServicer(evaluator_pb2_grpc.InspectionEvaluatorServicer):
    def __init__(self):
        self.core = EvaluatorCore(create_session())

    async def EvaluateDetections(self, request, context):
        try:
            logger.info(
                "EvaluateDetections req pc=%s pr=%s pl=%s det=%d",
                request.product_code,
                request.process_code,
                request.pipeline_id,
                len(request.detections),
            )
            criteria = await self.core.resolve_criteria(
                request.product_code, request.process_code, request.pipeline_id
            )
            if not criteria:
                logger.info("No criteria resolved -> PENDING judgment")
                return evaluator_pb2.EvaluationResponse(
                    judgment="PENDING", pipeline_id=request.pipeline_id, reason="criteria_not_found"
                )
            judgment, metrics = self.core.evaluate(request.detections, criteria)
            logger.info(
                "Decision=%s criteria=%s item=%s metrics=%s",
                judgment,
                criteria.get("criteria_id"),
                criteria.get("item_id"),
                metrics,
            )
            return evaluator_pb2.EvaluationResponse(
                judgment=judgment,
                criteria_id=criteria["criteria_id"],
                item_id=criteria["item_id"],
                pipeline_id=request.pipeline_id,
                metrics=metrics,
                reason=f"detected={metrics.get('detected')}",
            )
        except Exception as e:
            logger.exception("EvaluateDetections error: %s", e)
            return evaluator_pb2.EvaluationResponse(
                judgment="PENDING", pipeline_id=request.pipeline_id, reason=str(e)
            )


async def serve():
    port = int(os.getenv("GRPC_PORT", "9090"))
    server = grpc_aio.server()
    evaluator_pb2_grpc.add_InspectionEvaluatorServicer_to_server(InspectionEvaluatorServicer(), server)
    # Add standard gRPC health service so probes/monitors work
    class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
        def Check(self, request, context):
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

        def Watch(self, request, context):
            # Simple one-shot status stream
            yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

    health_pb2_grpc.add_HealthServicer_to_server(HealthServiceImplementation(), server)
    bind_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(bind_addr)
    logger.info(f"Inspection Evaluator gRPC serving at {bind_addr}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())

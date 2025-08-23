import asyncio
import logging
import os
from typing import Optional

import grpc
import grpc.aio as grpc_aio

import sys
from pathlib import Path

# Ensure generated protobufs are importable
generated_path = Path(__file__).resolve().parents[2] / "generated" / "python"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

logger = logging.getLogger(__name__)

try:
    from imageflow.v1 import evaluator_pb2, evaluator_pb2_grpc, ai_detection_pb2  # type: ignore

    HAS_EVAL_STUBS = True
except Exception as e:
    logger.warning(f"Evaluator gRPC stubs not available: {e}")
    HAS_EVAL_STUBS = False

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.inspection import (
    ProductTypeGroupMember,
    ProductTypeGroup,
    inspectionInstruction,
    InspectionItem,
    InspectionCriteria,
)


class EvaluationCore:
    async def resolve_criteria(
        self, product_code: str, process_code: str, pipeline_id: Optional[str]
    ):
        if not (product_code and process_code and pipeline_id):
            return None
        import uuid

        try:
            pipeline_uuid = uuid.UUID(pipeline_id)
        except Exception:
            return None
        async with AsyncSessionLocal() as session:
            grp_row = (
                await session.execute(
                    select(ProductTypeGroupMember, ProductTypeGroup)
                    .join(
                        ProductTypeGroup,
                        ProductTypeGroupMember.group_id == ProductTypeGroup.id,
                    )
                    .where(ProductTypeGroupMember.product_code == product_code)
                )
            ).first()
            if not grp_row:
                return None
            group_id = grp_row[0].group_id

            tgt = (
                (
                    await session.execute(
                        select(inspectionInstruction)
                        .where(
                            (inspectionInstruction.group_id == group_id)
                            & (inspectionInstruction.process_code == process_code)
                        )
                        .order_by(inspectionInstruction.created_at.desc())
                    )
                )
                .scalars()
                .first()
            )
            if not tgt:
                return None
            item = (
                (
                    await session.execute(
                        select(InspectionItem).where(
                            (InspectionItem.instruction_id == tgt.id)
                            & (InspectionItem.pipeline_id == pipeline_uuid)
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not item or not item.criteria_id:
                return None
            crit = (
                (
                    await session.execute(
                        select(InspectionCriteria).where(
                            InspectionCriteria.id == item.criteria_id
                        )
                    )
                )
                .scalars()
                .first()
            )
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
            return ok((det_count == 0) if expected else (det_count > 0)), {
                "detected": str(det_count)
            }
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
            return ok(decision), {
                "detected": str(det_count),
                "threshold": str(t),
                "operator": op,
            }
        if jt == "CATEGORICAL":
            allowed = set(spec.get("categorical", {}).get("allowed_categories", []))
            all_allowed = all((d.class_name in allowed) for d in detections)
            return ok(all_allowed), {
                "allowed": ",".join(allowed),
                "detected": str(det_count),
            }
        if jt == "NUMERICAL":
            num = spec.get("numerical", {})
            v = float(det_count)
            mn = num.get("min_value")
            mx = num.get("max_value")
            ok_min = True if mn is None else v >= float(mn)
            ok_max = True if mx is None else v <= float(mx)
            return ok(ok_min and ok_max), {
                "detected": str(det_count),
                "min": str(mn or ""),
                "max": str(mx or ""),
            }
        return ok(det_count == 0), {"detected": str(det_count)}

    async def resolve_criteria_by_item(self, item_id: str):
        """Resolve criteria directly from an item_id regardless of pipeline.
        Returns dict with keys: criteria_id, item_id, judgment_type, spec or None.
        """
        if not item_id:
            return None
        import uuid

        try:
            item_uuid = uuid.UUID(item_id)
        except Exception:
            return None
        async with AsyncSessionLocal() as session:
            item = (
                (
                    await session.execute(
                        select(InspectionItem).where(InspectionItem.id == item_uuid)
                    )
                )
                .scalars()
                .first()
            )
            if not item or not item.criteria_id:
                return None
            crit = (
                (
                    await session.execute(
                        select(InspectionCriteria).where(
                            InspectionCriteria.id == item.criteria_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not crit:
                return None
            return {
                "criteria_id": str(crit.id),
                "item_id": str(item.id),
                "judgment_type": crit.judgment_type,
                "spec": crit.spec,
            }


class InspectionEvaluatorServicer(evaluator_pb2_grpc.InspectionEvaluatorServicer):
    def __init__(self):
        self.core = EvaluationCore()

    async def EvaluateDetections(self, request, context):
        # Prefer explicit instruction item id in request body
        item_override: Optional[str] = getattr(request, "item_id", None) or None
        try:
            logger.info(
                "[evaluator-backend] EvaluateDetections: req.item_id=%s pc=%s pr=%s pl=%s det=%s",
                item_override,
                getattr(request, "product_code", None),
                getattr(request, "process_code", None),
                getattr(request, "pipeline_id", None),
                len(getattr(request, "detections", []) or []),
            )
        except Exception:
            pass

        criteria = None
        if item_override:
            criteria = await self.core.resolve_criteria_by_item(item_override)
            if criteria:
                try:
                    logger.info(
                        "[evaluator-backend] criteria resolved by item_id: item=%s criteria=%s",
                        criteria.get("item_id"),
                        criteria.get("criteria_id"),
                    )
                except Exception:
                    pass
        if not criteria:
            criteria = await self.core.resolve_criteria(
                request.product_code, request.process_code, request.pipeline_id
            )
            if criteria:
                try:
                    logger.info(
                        "[evaluator-backend] criteria resolved by pipeline: item=%s criteria=%s",
                        criteria.get("item_id"),
                        criteria.get("criteria_id"),
                    )
                except Exception:
                    pass
        if not criteria:
            return evaluator_pb2.EvaluationResponse(
                judgment="PENDING", pipeline_id=request.pipeline_id
            )
        judgment, metrics = self.core.evaluate(request.detections, criteria)
        return evaluator_pb2.EvaluationResponse(
            judgment=judgment,
            criteria_id=criteria["criteria_id"],
            item_id=criteria["item_id"],
            pipeline_id=request.pipeline_id,
            metrics=metrics,
            reason=f"detected={metrics.get('detected')}",
        )


class InspectionEvaluatorServer:
    def __init__(self, bind_addr: Optional[str] = None):
        self.bind_addr = bind_addr or os.getenv(
            "EVALUATOR_GRPC_BIND_ADDR", "0.0.0.0:50052"
        )
        self._server: Optional[grpc_aio.Server] = None

    async def start(self):
        if not HAS_EVAL_STUBS:
            logger.warning("Evaluator gRPC stubs not available; server will not start")
            return
        self._server = grpc_aio.server()
        evaluator_pb2_grpc.add_InspectionEvaluatorServicer_to_server(
            InspectionEvaluatorServicer(), self._server
        )
        self._server.add_insecure_port(self.bind_addr)
        await self._server.start()
        logger.info(f"Inspection Evaluator gRPC started at {self.bind_addr}")
        await self._server.wait_for_termination()

    async def stop(self, grace: float = 3.0):
        if self._server:
            await self._server.stop(grace)
            logger.info("Inspection Evaluator gRPC stopped")


_server_singleton: Optional[InspectionEvaluatorServer] = None


def get_evaluator_server() -> InspectionEvaluatorServer:
    global _server_singleton
    if _server_singleton is None:
        _server_singleton = InspectionEvaluatorServer()
    return _server_singleton

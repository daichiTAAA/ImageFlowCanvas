import asyncio
import logging
import os
from typing import AsyncIterator, Optional

import grpc
import grpc.aio as grpc_aio

# Ensure generated protobufs are importable
import sys
from pathlib import Path

generated_path = Path(__file__).resolve().parents[2] / "generated" / "python"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

from imageflow.v1 import camera_stream_pb2, camera_stream_pb2_grpc, ai_detection_pb2  # type: ignore

# JWT verification for gRPC metadata
from jose import jwt
from app.services import judgment_queue
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.inspection import (
    ProductTypeGroupMember,
    ProductTypeGroup,
    InspectionTarget,
    InspectionItem,
    InspectionCriteria,
)

logger = logging.getLogger(__name__)


class BackendCameraStreamProcessor(camera_stream_pb2_grpc.CameraStreamProcessorServicer):
    """
    gRPC server-side implementation that accepts frames from Desktop and
    proxies processing to the existing upstream camera-stream gRPC service.
    """

    def __init__(self):
        # Resolve upstream camera-stream endpoint (same logic as camera_stream.py)
        if os.getenv("NOMAD_ALLOC_ID"):
            endpoint = os.getenv("CAMERA_STREAM_GRPC_ENDPOINT", "192.168.5.15:9094")
        elif os.getenv("COMPOSE_PROJECT_NAME") or os.getenv("DOCKER_BUILDKIT"):
            endpoint = os.getenv("CAMERA_STREAM_GRPC_ENDPOINT", "camera-stream-grpc:9090")
        else:
            endpoint = os.getenv(
                "CAMERA_STREAM_GRPC_ENDPOINT",
                "camera-stream-grpc-service.image-processing.svc.cluster.local:9090",
            )

        self._endpoint = endpoint
        self._upstream_channel: Optional[grpc_aio.Channel] = None
        self._upstream_stub: Optional[
            camera_stream_pb2_grpc.CameraStreamProcessorStub
        ] = None
        # Create initial upstream connection (async)
        asyncio.get_event_loop().create_task(self._ensure_upstream())
        logger.info(f"Desktop gRPC bridge upstream endpoint: {endpoint}")

        # Auth config
        self._jwt_secret = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self._jwt_algo = os.getenv("JWT_ALGORITHM", "HS256")
        # Use in-process judgment queue for offloading aggregation

    def _verify_auth(self, context: grpc.ServicerContext) -> str:
        """Verify Authorization: Bearer <token> from gRPC metadata. Returns username (sub)."""
        try:
            md = dict(context.invocation_metadata())
            authz = md.get("authorization") or md.get("Authorization")
            if not authz or not authz.lower().startswith("bearer "):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid Authorization metadata")
            token = authz.split(" ", 1)[1].strip()
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algo])
            sub = payload.get("sub")
            if not sub:
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token payload")
            return sub
        except Exception as e:
            logger.warning(f"gRPC auth failed: {e}")
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Unauthorized")

    async def _ensure_upstream(self):
        """Ensure upstream aio channel/stub exists; recreate on failure."""
        try:
            ch = grpc_aio.insecure_channel(
                self._endpoint,
                options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 5000),
                    ("grpc.keepalive_permit_without_calls", True),
                    ("grpc.http2.min_time_between_pings_ms", 10000),
                ],
            )
            # Try a quick connectivity check (optional)
            self._upstream_channel = ch
            self._upstream_stub = camera_stream_pb2_grpc.CameraStreamProcessorStub(ch)
            logger.info("Upstream camera-stream gRPC (aio) initialized")
        except Exception as e:
            logger.error(f"Failed to init upstream channel: {e}")
            self._upstream_channel = None
            self._upstream_stub = None

    async def ProcessVideoStream(
        self,
        request_iterator: AsyncIterator[camera_stream_pb2.VideoFrame],
        context: grpc_aio.ServicerContext,  # type: ignore
    ) -> AsyncIterator[camera_stream_pb2.ProcessedFrame]:
        # Authenticate caller
        caller = self._verify_auth(context)
        logger.info(f"[gRPC] ProcessVideoStream start from caller={caller}")

        # Ensure upstream connectivity
        if not self._upstream_stub:
            logger.warning("[gRPC] Upstream stub missing; reinitializing...")
            await self._ensure_upstream()
        if not self._upstream_stub:
            logger.error("[gRPC] Upstream service unavailable after init attempt")
            context.abort(grpc.StatusCode.UNAVAILABLE, "Upstream service unavailable")

        # Wrap request iterator to pair each outgoing frame with its metadata
        meta_queue: asyncio.Queue = asyncio.Queue()

        async def wrapped_iterator():
            async for frame in request_iterator:
                meta = {
                    "source_id": frame.metadata.source_id,
                    "pipeline_id": frame.metadata.pipeline_id,
                    "width": frame.metadata.width,
                    "height": frame.metadata.height,
                    "processing_params": dict(frame.metadata.processing_params),
                }
                await meta_queue.put(meta)
                yield frame

        # Pass-through streaming with enrichment via evaluator service
        try:
            upstream_call = self._upstream_stub.ProcessVideoStream(wrapped_iterator())
            frame_count = 0
            async for processed in upstream_call:
                frame_count += 1
                if frame_count % 30 == 1:
                    logger.debug(f"[gRPC] Relaying processed frame #{frame_count} from upstream")
                # Pair with original metadata
                try:
                    meta = await asyncio.wait_for(meta_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    meta = {"processing_params": {}}

                # Compute judgment based on inspection criteria via evaluator
                enriched = await self._evaluate_via_service(processed, meta)
                yield enriched
        except grpc.RpcError as e:
            # Attempt one reconnection for transient errors
            logger.warning(f"[gRPC] Upstream RPC error: code={e.code()} details={e.details()}; attempting reconnection")
            await self._ensure_upstream()
            context.abort(grpc.StatusCode.UNAVAILABLE, f"Upstream stream failed: {e.details()}")
        except Exception as e:
            logger.exception(f"[gRPC] Bridge processing error: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Bridge processing error: {e}")

    async def _evaluate_and_enrich(self, processed: camera_stream_pb2.ProcessedFrame, meta: dict) -> camera_stream_pb2.ProcessedFrame:
        """(Deprecated) Local evaluation. Kept as fallback."""
        try:
            pp = meta.get("processing_params", {}) or {}
            product_code = pp.get("product_code")
            process_code = pp.get("process_code")
            pipeline_id = meta.get("pipeline_id")

            judgment = None  # "OK" or "NG"
            if product_code and process_code and pipeline_id:
                try:
                    import uuid

                    pipeline_uuid = uuid.UUID(pipeline_id)
                except Exception:
                    pipeline_uuid = None

                async with AsyncSessionLocal() as session:
                    criteria = await self._find_criteria(session, product_code, process_code, pipeline_uuid)
                    if criteria is not None:
                        judgment = self._judge_by_criteria(processed, criteria)

            # Build enriched frame (copy original and optionally append judgment as special detection)
            enriched = camera_stream_pb2.ProcessedFrame()
            enriched.processed_data = processed.processed_data
            enriched.source_id = processed.source_id
            enriched.processing_time_ms = processed.processing_time_ms
            enriched.status = processed.status
            if processed.error_message:
                enriched.error_message = processed.error_message
            if processed.HasField("processed_at"):
                enriched.processed_at.CopyFrom(processed.processed_at)

            # Copy detections
            for d in processed.detections:
                nd = enriched.detections.add()
                nd.class_name = d.class_name
                nd.confidence = d.confidence
                nd.bbox.x1 = d.bbox.x1
                nd.bbox.y1 = d.bbox.y1
                nd.bbox.x2 = d.bbox.x2
                nd.bbox.y2 = d.bbox.y2

            # Populate new proto fields when available; keep synthetic detection for backward compat
            if judgment:
                try:
                    enriched.judgment = judgment
                except Exception:
                    pass
                try:
                    if meta.get("pipeline_id"):
                        enriched.pipeline_id = meta.get("pipeline_id")
                except Exception:
                    pass
                try:
                    # criteria_id / item_id may be resolved by _find_criteria; return them via meta keys
                    if meta.get("criteria_id"):
                        enriched.criteria_id = str(meta.get("criteria_id"))
                except Exception:
                    pass
                try:
                    if meta.get("item_id"):
                        enriched.item_id = str(meta.get("item_id"))
                except Exception:
                    pass
                # Backward-compat synthetic detection
                jd = enriched.detections.add()
                jd.class_name = f"JUDGMENT:{judgment}"
                jd.confidence = 1.0
                jd.bbox.x1 = jd.bbox.y1 = jd.bbox.x2 = jd.bbox.y2 = 0.0
            
            return enriched
        except Exception as e:
            logger.warning(f"[gRPC] Enrichment failed, forwarding original frame: {e}")
            return processed

    async def _find_criteria(self, session, product_code: str, process_code: str, pipeline_uuid) -> dict | None:
        # Resolve group from product_code
        grp_row = (await session.execute(
            select(ProductTypeGroupMember, ProductTypeGroup)
            .join(ProductTypeGroup, ProductTypeGroupMember.group_id == ProductTypeGroup.id)
            .where(ProductTypeGroupMember.product_code == product_code)
        )).first()
        if not grp_row:
            return None
        group_id = grp_row[0].group_id

        # Find target for group + process
        tgt_row = (await session.execute(
            select(InspectionTarget)
            .where(
                (InspectionTarget.group_id == group_id) & (InspectionTarget.process_code == process_code)
            )
            .order_by(InspectionTarget.created_at.desc())
        )).scalars().first()
        if not tgt_row:
            return None

        # Find item by pipeline_id
        if pipeline_uuid is None:
            return None
        item = (await session.execute(
            select(InspectionItem).where(
                (InspectionItem.target_id == tgt_row.id) & (InspectionItem.pipeline_id == pipeline_uuid)
            )
        )).scalars().first()
        if not item or not item.criteria_id:
            return None

        crit = (await session.execute(
            select(InspectionCriteria).where(InspectionCriteria.id == item.criteria_id)
        )).scalars().first()
        if not crit:
            return None
        # Return meta IDs for enrichment
        return {
            "judgment_type": crit.judgment_type,
            "spec": crit.spec,
            "criteria_id": str(crit.id),
            "item_id": str(item.id),
        }

    def _judge_by_criteria(self, processed: camera_stream_pb2.ProcessedFrame, criteria: dict) -> str:
        det_count = len(processed.detections)
        jt = (criteria.get("judgment_type") or "").upper()
        spec = criteria.get("spec") or {}

        def decision(ok: bool) -> str:
            return "OK" if ok else "NG"

        if jt == "BINARY":
            expected = spec.get("binary", {}).get("expected_value", True)
            return decision((det_count == 0) if expected else (det_count > 0))
        if jt == "THRESHOLD":
            th = spec.get("threshold", {}).get("threshold")
            op = (spec.get("threshold", {}).get("operator") or "").upper()
            if th is None:
                return decision(det_count == 0)
            v = float(det_count)
            t = float(th)
            ok = {
                "LESS_THAN": v < t,
                "LESS_THAN_OR_EQUAL": v <= t,
                "GREATER_THAN": v > t,
                "GREATER_THAN_OR_EQUAL": v >= t,
                "EQUAL": v == t,
                "NOT_EQUAL": v != t,
            }.get(op, v <= t)
            return decision(ok)
        if jt == "CATEGORICAL":
            allowed = set(spec.get("categorical", {}).get("allowed_categories", []))
            all_allowed = all((d.class_name in allowed) for d in processed.detections)
            return decision(all_allowed)
        if jt == "NUMERICAL":
            num = spec.get("numerical", {})
            v = float(det_count)
            mn = num.get("min_value")
            mx = num.get("max_value")
            ok_min = True if mn is None else v >= float(mn)
            ok_max = True if mx is None else v <= float(mx)
            return decision(ok_min and ok_max)
        # Default fallback
        return decision(det_count == 0)

    async def _evaluate_via_service(self, processed: camera_stream_pb2.ProcessedFrame, meta: dict) -> camera_stream_pb2.ProcessedFrame:
        """Call inspection-evaluator-grpc; fallback to local if stubs/endpoint unavailable."""
        try:
            from imageflow.v1 import evaluator_pb2, evaluator_pb2_grpc
            # Prepare request
            pp = meta.get("processing_params", {}) or {}
            product_code = pp.get("product_code", "")
            process_code = pp.get("process_code", "")
            pipeline_id = meta.get("pipeline_id", "")
            req = evaluator_pb2.EvaluationRequest(
                product_code=product_code,
                process_code=process_code,
                pipeline_id=pipeline_id,
                detections=[
                    ai_detection_pb2.Detection(
                        class_name=d.class_name,
                        confidence=d.confidence,
                        bbox=ai_detection_pb2.BoundingBox(x1=d.bbox.x1, y1=d.bbox.y1, x2=d.bbox.x2, y2=d.bbox.y2),
                    )
                    for d in processed.detections
                ],
            )

            endpoint = os.getenv("EVALUATOR_GRPC_ENDPOINT", "127.0.0.1:50052")
            async with grpc_aio.insecure_channel(endpoint) as ch:
                stub = evaluator_pb2_grpc.InspectionEvaluatorStub(ch)
                resp = await stub.EvaluateDetections(req)

            # Build enriched ProcessedFrame with evaluator response
            enriched = camera_stream_pb2.ProcessedFrame()
            enriched.processed_data = processed.processed_data
            enriched.source_id = processed.source_id
            enriched.processing_time_ms = processed.processing_time_ms
            enriched.status = processed.status
            if processed.error_message:
                enriched.error_message = processed.error_message
            if processed.HasField("processed_at"):
                enriched.processed_at.CopyFrom(processed.processed_at)
            for d in processed.detections:
                nd = enriched.detections.add()
                nd.class_name = d.class_name
                nd.confidence = d.confidence
                nd.bbox.x1 = d.bbox.x1
                nd.bbox.y1 = d.bbox.y1
                nd.bbox.x2 = d.bbox.x2
                nd.bbox.y2 = d.bbox.y2
            # Set new fields
            if resp.judgment:
                try:
                    enriched.judgment = resp.judgment
                except Exception:
                    pass
            if resp.criteria_id:
                try:
                    enriched.criteria_id = resp.criteria_id
                except Exception:
                    pass
            if resp.item_id:
                try:
                    enriched.item_id = resp.item_id
                except Exception:
                    pass
            if resp.pipeline_id:
                try:
                    enriched.pipeline_id = resp.pipeline_id
                except Exception:
                    pass
            # Offload aggregation & DB reflection to Backend Worker via in-process queue
            try:
                pp = meta.get("processing_params", {}) or {}
                exec_id = pp.get("execution_id")
                item_exec_id = pp.get("item_execution_id")
                if resp.judgment and exec_id and item_exec_id:
                    await judgment_queue.publish({
                        "execution_id": exec_id,
                        "item_execution_id": item_exec_id,
                        "judgment": resp.judgment,
                        "criteria_id": resp.criteria_id,
                        "item_id": resp.item_id,
                        "pipeline_id": resp.pipeline_id,
                        "metrics": dict(resp.metrics),
                    })
            except Exception as pe:
                logger.warning(f"[gRPC] Emit judgment event failed: {pe}")
            return enriched
        except Exception as e:
            logger.error(f"[gRPC] Evaluator call failed: {e}")
            # No fallback; return original processed frame without judgment
            return processed


class DesktopGrpcServer:
    def __init__(self, bind_addr: str | None = None):
        self.bind_addr = bind_addr or os.getenv("DESKTOP_GRPC_BIND_ADDR", "0.0.0.0:50051")
        self._server: grpc.aio.Server | None = None

    async def start(self):
        self._server = grpc_aio.server(options=[
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 5000),
            ("grpc.keepalive_permit_without_calls", True),
        ])
        camera_stream_pb2_grpc.add_CameraStreamProcessorServicer_to_server(
            BackendCameraStreamProcessor(), self._server
        )
        # Optional TLS: provide cert/key via env to enable secure port
        cert_path = os.getenv("DESKTOP_GRPC_TLS_CERT")
        key_path = os.getenv("DESKTOP_GRPC_TLS_KEY")
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            with open(cert_path, "rb") as f:
                cert_chain = f.read()
            with open(key_path, "rb") as f:
                private_key = f.read()
            server_creds = grpc.ssl_server_credentials(((private_key, cert_chain),))
            self._server.add_secure_port(self.bind_addr, server_creds)
            logger.info(f"gRPC TLS enabled on {self.bind_addr}")
        else:
            self._server.add_insecure_port(self.bind_addr)
            logger.info(f"gRPC insecure on {self.bind_addr}")
        await self._server.start()
        logger.info(f"Desktop gRPC server started on {self.bind_addr}")
        await self._server.wait_for_termination()

    async def stop(self, grace: float = 3.0):
        if self._server:
            await self._server.stop(grace)
            logger.info("Desktop gRPC server stopped")


# Singleton helpers
_grpc_server_instance: DesktopGrpcServer | None = None


def get_grpc_server() -> DesktopGrpcServer:
    global _grpc_server_instance
    if _grpc_server_instance is None:
        _grpc_server_instance = DesktopGrpcServer()
    return _grpc_server_instance

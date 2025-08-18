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

from imageflow.v1 import camera_stream_pb2, camera_stream_pb2_grpc  # type: ignore

# JWT verification for gRPC metadata
from jose import jwt

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

        # Pass-through streaming: forward inbound frames to upstream and stream responses back
        try:
            upstream_call = self._upstream_stub.ProcessVideoStream(request_iterator)
            frame_count = 0
            async for processed in upstream_call:
                frame_count += 1
                if frame_count % 30 == 1:
                    logger.debug(f"[gRPC] Relaying processed frame #{frame_count} from upstream")
                yield processed
        except grpc.RpcError as e:
            # Attempt one reconnection for transient errors
            logger.warning(f"[gRPC] Upstream RPC error: code={e.code()} details={e.details()}; attempting reconnection")
            await self._ensure_upstream()
            context.abort(grpc.StatusCode.UNAVAILABLE, f"Upstream stream failed: {e.details()}")
        except Exception as e:
            logger.exception(f"[gRPC] Bridge processing error: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Bridge processing error: {e}")


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

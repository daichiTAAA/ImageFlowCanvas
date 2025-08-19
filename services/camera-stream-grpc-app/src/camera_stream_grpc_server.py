import sys
import os
import time
import logging
import asyncio
from concurrent import futures
from datetime import datetime, timezone
import threading
import queue
import json
import requests
from typing import Dict, List, Any, Optional

import grpc
import cv2
import numpy as np
from PIL import Image
import io
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto path
sys.path.append("/app/generated/python")
sys.path.append("/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python")

from imageflow.v1 import camera_stream_pb2
from imageflow.v1 import camera_stream_pb2_grpc
from imageflow.v1 import ai_detection_pb2
from imageflow.v1 import ai_detection_pb2_grpc
from imageflow.v1 import resize_pb2
from imageflow.v1 import resize_pb2_grpc
from imageflow.v1 import filter_pb2
from imageflow.v1 import filter_pb2_grpc
from imageflow.v1 import common_pb2
from grpc_health.v1 import health_pb2, health_pb2_grpc
from imageflow.v1 import evaluator_pb2
from imageflow.v1 import evaluator_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CameraStreamProcessorImplementation(
    camera_stream_pb2_grpc.CameraStreamProcessorServicer
):
    def __init__(self):
        # Detect deployment environment and set appropriate default endpoints
        self.deployment_env = os.getenv("DEPLOYMENT_ENV", "nomad")  # nomad, k3s, docker

        # Set default endpoints based on environment
        if self.deployment_env == "k3s":
            # Kubernetes service discovery
            resize_default = (
                "resize-grpc-service.image-processing.svc.cluster.local:9090"
            )
            ai_detection_default = (
                "ai-detection-grpc-service.image-processing.svc.cluster.local:9090"
            )
            filter_default = (
                "filter-grpc-service.image-processing.svc.cluster.local:9090"
            )
            backend_default = "http://backend-service.default.svc.cluster.local:8000"
            evaluator_default = (
                "inspection-evaluator-grpc-service.image-processing.svc.cluster.local:9090"
            )
        elif self.deployment_env == "docker":
            # Docker Compose service names
            resize_default = "resize-grpc:9090"
            ai_detection_default = "ai-detection-grpc:9090"
            filter_default = "filter-grpc:9090"
            backend_default = "http://backend:8000"
            evaluator_default = "inspection-evaluator-grpc:9090"
        else:
            # Nomad with direct IP addressing
            nomad_ip = os.getenv("NOMAD_IP", "192.168.5.15")
            resize_default = f"{nomad_ip}:9092"
            ai_detection_default = f"{nomad_ip}:9091"
            filter_default = f"{nomad_ip}:9093"
            backend_default = f"http://{nomad_ip}:8000"
            evaluator_default = f"{nomad_ip}:9094"

        # gRPC service endpoints with environment-aware defaults
        self.grpc_services = {
            "resize": {
                "endpoint": os.getenv("RESIZE_GRPC_ENDPOINT", resize_default),
                "client_class": resize_pb2_grpc.ResizeServiceStub,
                "timeout": 30.0,
            },
            "ai_detection": {
                "endpoint": os.getenv(
                    "AI_DETECTION_GRPC_ENDPOINT", ai_detection_default
                ),
                "client_class": ai_detection_pb2_grpc.AIDetectionServiceStub,
                "timeout": 60.0,
            },
            "filter": {
                "endpoint": os.getenv("FILTER_GRPC_ENDPOINT", filter_default),
                "client_class": filter_pb2_grpc.FilterServiceStub,
                "timeout": 30.0,
            },
            "evaluator": {
                "endpoint": os.getenv(
                    "EVALUATOR_GRPC_ENDPOINT", evaluator_default
                ),
                "client_class": evaluator_pb2_grpc.InspectionEvaluatorStub,
                "timeout": 10.0,
            },
        }

        # Backend API endpoint for pipeline definitions
        self.backend_api_url = os.getenv("BACKEND_API_URL", backend_default)

        # Service-to-service authentication bypass
        self.service_auth_token = os.getenv("SERVICE_AUTH_TOKEN", None)
        self.skip_auth = os.getenv("SKIP_SERVICE_AUTH", "true").lower() == "true"

        # Frame processing parameters
        self.max_concurrent_streams = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
        self.frame_skip_threshold = int(
            os.getenv("FRAME_SKIP_THRESHOLD", "1000")
        )  # ms - 1秒に延長

        # Initialize gRPC connections
        self.channels = {}
        self.clients = {}
        self._initialize_grpc_connections()

        # Cache for pipeline definitions
        self._pipeline_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

        logger.info(f"CameraStreamProcessor initialized")
        logger.info(f"Deployment environment: {self.deployment_env}")
        logger.info(f"Backend API: {self.backend_api_url}")
        logger.info(f"Max concurrent streams: {self.max_concurrent_streams}")
        for service_name, config in self.grpc_services.items():
            logger.info(f"{service_name} service: {config['endpoint']}")

    def _initialize_grpc_connections(self):
        """Initialize persistent gRPC connections to services"""
        for service_name, config in self.grpc_services.items():
            try:
                channel = grpc.insecure_channel(
                    config["endpoint"],
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 5000),
                        ("grpc.keepalive_permit_without_calls", True),
                        ("grpc.http2.max_pings_without_data", 0),
                        ("grpc.http2.min_time_between_pings_ms", 10000),
                        ("grpc.http2.min_ping_interval_without_data_ms", 300000),
                    ],
                )

                client = config["client_class"](channel)

                self.channels[service_name] = channel
                self.clients[service_name] = client

                logger.info(
                    f"Initialized gRPC connection to {service_name}: {config['endpoint']}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to initialize gRPC connection to {service_name}: {e}"
                )

    def _get_pipeline_definition(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline definition from backend API with caching"""
        current_time = time.time()

        # Check cache validity
        if (current_time - self._cache_timestamp) > self._cache_ttl:
            self._pipeline_cache.clear()
            self._cache_timestamp = current_time

        # Return cached pipeline if available
        if pipeline_id in self._pipeline_cache:
            return self._pipeline_cache[pipeline_id]

        try:
            # Fetch pipeline definition from backend API
            # Prepare headers for service-to-service authentication
            headers = {}

            # Add service bypass header for internal communication
            if self.skip_auth:
                headers["X-Service-Internal"] = "true"
                headers["X-Service-Name"] = "camera-stream-grpc"
                logger.debug(f"Added service bypass headers: {headers}")

            # Add service token if available
            if self.service_auth_token:
                headers["Authorization"] = f"Bearer {self.service_auth_token}"
                logger.debug(f"Added service token to headers")

            logger.debug(
                f"Making request to: {self.backend_api_url}/v1/pipelines/{pipeline_id}"
            )
            logger.debug(f"Request headers: {headers}")

            response = requests.get(
                f"{self.backend_api_url}/v1/pipelines/{pipeline_id}",
                headers=headers,
                timeout=5,
            )
            if response.status_code == 200:
                pipeline_def = response.json()
                self._pipeline_cache[pipeline_id] = pipeline_def
                logger.info(f"Fetched pipeline definition for {pipeline_id}")
                return pipeline_def
            else:
                logger.warning(
                    f"Failed to fetch pipeline {pipeline_id}: HTTP {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error fetching pipeline definition for {pipeline_id}: {e}")
            return None

    def ProcessVideoStream(self, request_iterator, context):
        """
        Bidirectional streaming RPC for real-time video processing
        """
        client_id = context.peer()
        logger.info(f"New video stream started from {client_id}")

        try:
            # Process incoming video frames
            for video_frame in request_iterator:
                start_time = time.time()

                try:
                    # Process the frame
                    processed_frame = self._process_video_frame(video_frame)
                    yield processed_frame

                    processing_time = (time.time() - start_time) * 1000
                    logger.debug(
                        f"Frame processed in {processing_time:.2f}ms for source {video_frame.metadata.source_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing frame from {video_frame.metadata.source_id}: {e}"
                    )

                    # Send error response
                    error_frame = camera_stream_pb2.ProcessedFrame()
                    error_frame.source_id = video_frame.metadata.source_id
                    error_frame.status = (
                        camera_stream_pb2.STREAM_PROCESSING_STATUS_FAILED
                    )
                    error_frame.error_message = str(e)

                    timestamp = Timestamp()
                    timestamp.GetCurrentTime()
                    error_frame.processed_at.CopyFrom(timestamp)

                    yield error_frame

        except Exception as e:
            logger.error(f"Stream error for {client_id}: {e}")
        finally:
            logger.info(f"Video stream ended for {client_id}")

    def _process_video_frame(self, video_frame):
        """
        Process a single video frame through the defined pipeline
        """
        start_time = time.time()

        # Create response frame
        processed_frame = camera_stream_pb2.ProcessedFrame()
        processed_frame.source_id = video_frame.metadata.source_id

        # フレーム受信時の詳細ログ
        logger.debug(f"=== Processing Video Frame ===")
        logger.debug(f"Source ID: {video_frame.metadata.source_id}")
        logger.debug(f"Pipeline ID: {video_frame.metadata.pipeline_id}")
        logger.debug(f"Frame data size: {len(video_frame.frame_data)} bytes")
        logger.debug(
            f"Frame dimensions: {video_frame.metadata.width}x{video_frame.metadata.height}"
        )

        try:
            # Check if we should skip this frame for performance
            if self._should_skip_frame(video_frame):
                processed_frame.status = (
                    camera_stream_pb2.STREAM_PROCESSING_STATUS_SKIPPED
                )
                processed_frame.error_message = "Frame skipped due to high load"
                logger.info(
                    f"Frame SKIPPED for source {video_frame.metadata.source_id}"
                )
                return processed_frame

            # Get pipeline definition based on metadata
            pipeline_id = video_frame.metadata.pipeline_id

            if pipeline_id and pipeline_id != "passthrough":
                # Get pipeline definition from backend
                pipeline_def = self._get_pipeline_definition(pipeline_id)
                if pipeline_def:
                    # Process frame through the defined pipeline
                    result = self._execute_pipeline(video_frame, pipeline_def)
                    if result:
                        processed_frame.detections.extend(result.get("detections", []))
                        if "processed_data" in result:
                            processed_frame.processed_data = result["processed_data"]
                        processed_frame.status = (
                            camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
                        )
                        # Populate pipeline id always for downstream mapping
                        if pipeline_id:
                            processed_frame.pipeline_id = pipeline_id

                        # Try to evaluate detections via inspection-evaluator service
                        try:
                            eval_judgment, eval_item_id, eval_criteria_id = self._evaluate_detections(
                                video_frame, list(result.get("detections", []))
                            )
                            if eval_judgment:
                                processed_frame.judgment = eval_judgment
                            if eval_item_id:
                                processed_frame.item_id = eval_item_id
                            if eval_criteria_id:
                                processed_frame.criteria_id = eval_criteria_id
                        except Exception as e:
                            logger.warning(f"Evaluator call failed: {e}")
                    else:
                        processed_frame.status = (
                            camera_stream_pb2.STREAM_PROCESSING_STATUS_FAILED
                        )
                        processed_frame.error_message = "Pipeline execution failed"
                else:
                    # Pipeline not found, fallback to passthrough
                    processed_frame.processed_data = video_frame.frame_data
                    processed_frame.status = (
                        camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
                    )
                    logger.warning(
                        f"Pipeline {pipeline_id} not found, using passthrough"
                    )
            else:
                # Simple passthrough for testing or when no pipeline specified
                processed_frame.processed_data = video_frame.frame_data
                processed_frame.status = (
                    camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
                )

            # Set timing information
            processing_time = (time.time() - start_time) * 1000
            processed_frame.processing_time_ms = int(processing_time)

            # Set timestamp
            timestamp = Timestamp()
            timestamp.GetCurrentTime()
            processed_frame.processed_at.CopyFrom(timestamp)

            return processed_frame

        except Exception as e:
            logger.error(f"Error in frame processing: {e}")
            processed_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_FAILED
            processed_frame.error_message = str(e)
            return processed_frame

    def _evaluate_detections(self, video_frame, detections_list: List[ai_detection_pb2.Detection]):
        """
        Call the inspection-evaluator to obtain server-side judgment.
        Returns (judgment, item_id, criteria_id) or (None, None, None) on failure.
        """
        if "evaluator" not in self.clients:
            return (None, None, None)
        try:
            client = self.clients["evaluator"]
            product_code = video_frame.metadata.processing_params.get("product_code", "")
            process_code = video_frame.metadata.processing_params.get("process_code", "")
            pipeline_id = video_frame.metadata.pipeline_id or ""
            # Build request
            target_item_id = video_frame.metadata.processing_params.get("target_item_id", "")
            req = evaluator_pb2.EvaluationRequest(
                product_code=product_code,
                process_code=process_code,
                pipeline_id=pipeline_id,
                detections=detections_list,
                item_id=target_item_id or "",
            )
            resp = client.EvaluateDetections(req, timeout=self.grpc_services["evaluator"]["timeout"])
            logger.debug(
                f"Evaluator resp: judgment={resp.judgment} item_id={resp.item_id} criteria_id={resp.criteria_id}"
            )
            return (resp.judgment or None, resp.item_id or None, resp.criteria_id or None)
        except Exception as e:
            logger.warning(f"EvaluateDetections error: {e}")
            return (None, None, None)

    def _should_skip_frame(self, video_frame):
        """
        Determine if frame should be skipped based on load
        """
        # Simple heuristic: check frame age
        current_time = int(time.time() * 1000)
        frame_timestamp = video_frame.timestamp_ms
        frame_age = current_time - frame_timestamp

        # 時刻情報をより詳細にログ出力
        from datetime import datetime

        current_datetime = datetime.fromtimestamp(current_time / 1000.0)
        frame_datetime = datetime.fromtimestamp(frame_timestamp / 1000.0)

        logger.debug(f"=== Frame Timing Analysis ===")
        logger.debug(
            f"Current time: {current_time}ms ({current_datetime.strftime('%H:%M:%S.%f')[:-3]})"
        )
        logger.debug(
            f"Frame timestamp: {frame_timestamp}ms ({frame_datetime.strftime('%H:%M:%S.%f')[:-3]})"
        )
        logger.debug(f"Frame age: {frame_age}ms")
        logger.debug(f"Skip threshold: {self.frame_skip_threshold}ms")
        logger.debug(f"Will skip: {frame_age > self.frame_skip_threshold}")

        if frame_age > self.frame_skip_threshold:
            logger.warning(
                f"SKIPPING old frame - Age: {frame_age}ms > Threshold: {self.frame_skip_threshold}ms"
            )
            return True

        logger.debug(
            f"PROCESSING frame - Age: {frame_age}ms <= Threshold: {self.frame_skip_threshold}ms"
        )
        return False

    def _execute_pipeline(
        self, video_frame, pipeline_def: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute the pipeline defined in Web UI through real gRPC services
        """
        try:
            components = pipeline_def.get("components", [])
            if not components:
                logger.warning("Pipeline has no components")
                return None

            # Sort components by dependencies to determine execution order
            execution_order = self._sort_components_by_dependencies(components)

            # Start with the original frame data
            current_data = video_frame.frame_data
            result = {"detections": [], "processed_data": current_data}

            # Execute each component in order
            for component in execution_order:
                component_type = component.get("component_type", "")
                component_params = component.get("parameters", {})

                logger.debug(f"Executing component: {component_type}")

                if component_type == "resize":
                    current_data = self._execute_resize(current_data, component_params)
                elif component_type == "ai_detection":
                    detections = self._execute_ai_detection(
                        current_data,
                        component_params,
                        video_frame.metadata.width,
                        video_frame.metadata.height,
                    )
                    result["detections"].extend(detections)
                elif component_type == "filter":
                    current_data = self._execute_filter(current_data, component_params)
                else:
                    logger.warning(f"Unknown component type: {component_type}")

                # Update processed data after each step
                result["processed_data"] = current_data

            return result

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}")
            return None

    def _sort_components_by_dependencies(
        self, components: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sort components by their dependencies to determine execution order
        """
        # For real-time processing, we'll use a simple ordering strategy
        # AI detection should run before filters, resize can be anywhere
        order_priority = {
            "resize": 1,
            "ai_detection": 2,
            "filter": 3,
        }

        return sorted(
            components,
            key=lambda c: order_priority.get(c.get("component_type", ""), 999),
        )

    def _execute_resize(self, frame_data: bytes, params: Dict[str, Any]) -> bytes:
        """Execute resize operation through gRPC service"""
        try:
            if "resize" not in self.clients:
                logger.error("Resize gRPC client not available")
                return frame_data

            client = self.clients["resize"]

            # Create resize request
            request = resize_pb2.ResizeRequest()

            # Create ImageBytes for input_bytes
            image_bytes = common_pb2.ImageBytes()
            image_bytes.data = frame_data
            image_bytes.format = "JPEG"

            request.input_bytes.CopyFrom(image_bytes)
            request.target_width = params.get("width", 640)
            request.target_height = params.get("height", 480)

            # Call resize service
            response = client.ResizeImage(
                request, timeout=self.grpc_services["resize"]["timeout"]
            )

            if response.result.status == common_pb2.PROCESSING_STATUS_COMPLETED:
                # Check if we have direct output data (for real-time processing)
                if response.result.output_data:
                    return response.result.output_data
                # Otherwise use MinIO reference data (shouldn't happen in real-time)
                else:
                    logger.error("Resize failed: No output data in response")
                    return frame_data
            else:
                logger.error(f"Resize failed: {response.result.message}")
                return frame_data

        except Exception as e:
            logger.error(f"Resize execution error: {e}")
            return frame_data

    def _execute_ai_detection(
        self, frame_data: bytes, params: Dict[str, Any], width: int = 0, height: int = 0
    ) -> List[ai_detection_pb2.Detection]:
        """Execute AI detection through gRPC service"""
        try:
            if "ai_detection" not in self.clients:
                logger.error("AI Detection gRPC client not available")
                return []

            client = self.clients["ai_detection"]

            # Create detection request
            request = ai_detection_pb2.DetectionRequest()

            # Create ImageBytes for input_bytes
            image_bytes = common_pb2.ImageBytes()
            image_bytes.data = frame_data
            image_bytes.format = "JPEG"
            image_bytes.width = width
            image_bytes.height = height

            request.input_bytes.CopyFrom(image_bytes)
            request.model_name = params.get("model_name", "yolo11n")
            request.confidence_threshold = params.get("confidence_threshold", 0.5)

            # Call AI detection service
            response = client.DetectObjects(
                request, timeout=self.grpc_services["ai_detection"]["timeout"]
            )

            if response.result.status == common_pb2.PROCESSING_STATUS_COMPLETED:
                # Return AI detection results directly (they're already in the correct format)
                return list(response.detections)
            else:
                logger.error(f"AI detection failed: {response.error_message}")
                return []

        except Exception as e:
            logger.error(f"AI detection execution error: {e}")
            return []

    def _execute_filter(self, frame_data: bytes, params: Dict[str, Any]) -> bytes:
        """Execute filter operation through gRPC service"""
        try:
            if "filter" not in self.clients:
                logger.error("Filter gRPC client not available")
                return frame_data

            client = self.clients["filter"]

            # Create filter request
            request = filter_pb2.FilterRequest()

            # Create ImageBytes for input_bytes
            image_bytes = common_pb2.ImageBytes()
            image_bytes.data = frame_data
            image_bytes.format = "JPEG"

            request.input_bytes.CopyFrom(image_bytes)
            request.filter_type = params.get("filter_type", filter_pb2.FILTER_TYPE_BLUR)

            # Add filter parameters
            for key, value in params.items():
                if key != "filter_type":
                    request.parameters[key] = str(value)

            # Call filter service
            response = client.ApplyFilter(
                request, timeout=self.grpc_services["filter"]["timeout"]
            )

            if response.result.status == common_pb2.PROCESSING_STATUS_COMPLETED:
                # Check if we have direct output data (for real-time processing)
                if response.result.output_data:
                    return response.result.output_data
                # Otherwise use MinIO reference data (shouldn't happen in real-time)
                else:
                    logger.error("Filter failed: No output data in response")
                    return frame_data
            else:
                logger.error(f"Filter failed: {response.result.message}")
                return frame_data

        except Exception as e:
            logger.error(f"Filter execution error: {e}")
            return frame_data

    def _validate_frame(self, frame_data):
        """
        Basic frame validation
        """
        if not frame_data:
            raise ValueError("Empty frame data")

        # Try to decode the image to validate format
        try:
            image = Image.open(io.BytesIO(frame_data))
            if image.size[0] < 64 or image.size[1] < 64:
                raise ValueError("Frame too small")
        except Exception as e:
            raise ValueError(f"Invalid image format: {e}")


class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING
        )


def serve():
    port = os.getenv("GRPC_PORT", "9090")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add services
    camera_stream_pb2_grpc.add_CameraStreamProcessorServicer_to_server(
        CameraStreamProcessorImplementation(), server
    )
    health_pb2_grpc.add_HealthServicer_to_server(HealthServiceImplementation(), server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"Camera Stream gRPC server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)


if __name__ == "__main__":
    serve()

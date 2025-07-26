"""
Direct gRPC Pipeline Executor
High-performance direct gRPC service calls for 40-100ms execution times
"""

import asyncio
import grpc
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Import generated gRPC stubs
import sys
import os

# Add the correct path for generated protobuf files
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
generated_path = os.path.join(backend_root, "generated", "python")
if generated_path not in sys.path:
    sys.path.insert(0, generated_path)

# Initialize logger first
logger = logging.getLogger(__name__)

try:
    from imageflow.v1 import (
        resize_pb2,
        resize_pb2_grpc,
        ai_detection_pb2,
        ai_detection_pb2_grpc,
        filter_pb2,
        filter_pb2_grpc,
        common_pb2,
    )

    logger.info("Successfully imported protobuf files")
except ImportError as e:
    logger.error(f"Failed to import protobuf files: {e}")
    logger.error(f"Generated path: {generated_path}")
    logger.error(f"Generated path exists: {os.path.exists(generated_path)}")
    if os.path.exists(generated_path):
        logger.error(f"Contents: {os.listdir(generated_path)}")
    raise ImportError(
        f"Cannot start gRPC pipeline executor without protobuf files: {e}"
    )

from app.models.execution import ExecutionStatus, ExecutionStep, StepStatus
from app.services.kafka_service import KafkaService


class GRPCPipelineExecutor:
    """
    Direct gRPC pipeline executor for ultra-fast image processing
    Achieves 40-100ms execution times with direct service calls
    """

    def __init__(self):
        # Environment detection for gRPC service endpoints
        is_nomad = os.getenv("NOMAD_ALLOC_ID") is not None
        is_compose = (
            os.getenv("COMPOSE_PROJECT_NAME") is not None
            or os.getenv("DOCKER_COMPOSE") is not None
        )

        # Service endpoint configuration based on environment
        if is_nomad:
            # Nomad environment - use direct IP addresses with correct ports
            logger.info("Detected Nomad environment - using direct IP endpoints")
            default_resize_endpoint = "192.168.5.15:9090"
            default_ai_detection_endpoint = (
                "192.168.5.15:9091"  # Port 9091 for AI detection
            )
            default_filter_endpoint = "192.168.5.15:9093"
        elif is_compose:
            # Docker Compose environment - use service names
            logger.info(
                "Detected Docker Compose environment - using service name endpoints"
            )
            default_resize_endpoint = "resize-grpc:9090"
            default_ai_detection_endpoint = "ai-detection-grpc:9090"
            default_filter_endpoint = "filter-grpc:9090"
        else:
            # Kubernetes environment - use full service DNS
            logger.info("Detected Kubernetes environment - using cluster DNS endpoints")
            default_resize_endpoint = (
                "resize-grpc-service.image-processing.svc.cluster.local:9090"
            )
            default_ai_detection_endpoint = (
                "ai-detection-grpc-service.image-processing.svc.cluster.local:9090"
            )
            default_filter_endpoint = (
                "filter-grpc-service.image-processing.svc.cluster.local:9090"
            )

        self.grpc_services = {
            "resize": {
                "endpoint": os.getenv(
                    "RESIZE_GRPC_ENDPOINT",
                    default_resize_endpoint,
                ),
                "client_class": resize_pb2_grpc.ResizeServiceStub,
                "timeout": 30.0,
            },
            "ai_detection": {
                "endpoint": os.getenv(
                    "AI_DETECTION_GRPC_ENDPOINT",
                    default_ai_detection_endpoint,
                ),
                "client_class": ai_detection_pb2_grpc.AIDetectionServiceStub,
                "timeout": 60.0,
            },
            "filter": {
                "endpoint": os.getenv(
                    "FILTER_GRPC_ENDPOINT",
                    default_filter_endpoint,
                ),
                "client_class": filter_pb2_grpc.FilterServiceStub,
                "timeout": 30.0,
            },
        }

        self.kafka_service = KafkaService()
        self.channels = {}
        self.clients = {}

        # Initialize gRPC connections
        self._initialize_grpc_connections()

    def _initialize_grpc_connections(self):
        """Initialize persistent gRPC connections to services"""
        for service_name, config in self.grpc_services.items():
            try:
                channel = grpc.aio.insecure_channel(
                    config["endpoint"],
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 5000),
                        ("grpc.keepalive_permit_without_calls", True),
                        ("grpc.http2.keepalive_timeout_ms", 5000),
                        ("grpc.max_connection_idle_ms", 10000),
                    ],
                )

                client = config["client_class"](channel)

                self.channels[service_name] = channel
                self.clients[service_name] = client

                logger.info(
                    f"Initialized gRPC connection to {service_name} at {config['endpoint']}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to initialize gRPC connection to {service_name}: {e}"
                )

    async def execute_pipeline(
        self, pipeline_config: Dict[str, Any], execution_id: str
    ) -> Dict[str, Any]:
        """
        Execute pipeline with direct gRPC calls for 40-100ms performance

        Args:
            pipeline_config: Pipeline configuration with steps and parameters
            execution_id: Unique execution identifier

        Returns:
            Execution result with timing and output information
        """
        start_time = time.time()

        try:
            logger.info(f"Starting direct gRPC pipeline execution: {execution_id}")

            # Parse pipeline steps and resolve dependencies
            steps = pipeline_config.get("steps", [])
            global_params = pipeline_config.get("globalParameters", {})

            execution_order = self._resolve_step_dependencies(steps)

            results = {}
            current_image_path = global_params.get("inputPath")

            # Execute pipeline steps in optimized order
            for step_group in execution_order:
                if len(step_group) == 1:
                    # Single step execution
                    step = step_group[0]
                    result = await self._execute_step(
                        step, current_image_path, execution_id
                    )
                    results[step["stepId"]] = result
                    current_image_path = result["output_path"]

                    # Send progress notification
                    await self._send_progress_notification(
                        execution_id, step["stepId"], "completed", result
                    )

                else:
                    # Parallel step execution
                    tasks = []
                    for step in step_group:
                        task = asyncio.create_task(
                            self._execute_step(step, current_image_path, execution_id)
                        )
                        tasks.append((step, task))

                    # Wait for all parallel tasks to complete
                    for step, task in tasks:
                        try:
                            result = await task
                            results[step["stepId"]] = result
                            await self._send_progress_notification(
                                execution_id, step["stepId"], "completed", result
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to execute step {step['stepId']}: {e}"
                            )
                            results[step["stepId"]] = {
                                "status": "failed",
                                "error": str(e),
                            }
                            await self._send_progress_notification(
                                execution_id,
                                step["stepId"],
                                "failed",
                                {"error": str(e)},
                            )

            execution_time = time.time() - start_time

            return {
                "execution_id": execution_id,
                "status": "completed",
                "execution_time_ms": execution_time * 1000,
                "results": results,
                "final_output_path": current_image_path,
            }

        except Exception as e:
            logger.error(f"Pipeline execution failed for {execution_id}: {e}")
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

    async def _execute_step(
        self, step: Dict[str, Any], input_path: str, execution_id: str
    ) -> Dict[str, Any]:
        """Execute individual pipeline step via direct gRPC call"""
        step_start_time = time.time()
        component_name = step.get("componentName")
        step_id = step.get("stepId")

        logger.info(
            f"Executing step {step_id} ({component_name}) for execution {execution_id}"
        )

        # Send start notification
        await self._send_progress_notification(execution_id, step_id, "running", {})

        try:
            if component_name == "resize":
                result = await self._execute_resize_step(step, input_path, execution_id)
            elif component_name == "ai_detection":
                result = await self._execute_ai_detection_step(
                    step, input_path, execution_id
                )
            elif component_name == "filter":
                result = await self._execute_filter_step(step, input_path, execution_id)
            else:
                raise ValueError(f"Unknown component: {component_name}")

            processing_time = (time.time() - step_start_time) * 1000

            return {
                "step_id": step_id,
                "component_name": component_name,
                "output_path": result.get("output_path"),
                "processing_time_ms": processing_time,
                "status": "success",
                "metadata": result.get("metadata", {}),
            }

        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}")
            return {
                "step_id": step_id,
                "component_name": component_name,
                "status": "failed",
                "error": str(e),
                "processing_time_ms": (time.time() - step_start_time) * 1000,
            }

    async def _execute_resize_step(
        self, step: Dict[str, Any], input_path: str, execution_id: str
    ) -> Dict[str, Any]:
        """Execute resize step via direct gRPC call"""
        parameters = step.get("parameters", {})

        # Create gRPC request
        request = resize_pb2.ResizeRequest(
            input_image=common_pb2.ImageData(
                bucket="imageflow-files",
                object_key=input_path,
                content_type="image/jpeg",
            ),
            target_width=int(parameters.get("width", 800)),
            target_height=int(parameters.get("height", 600)),
            maintain_aspect_ratio=parameters.get("maintain_aspect_ratio", True),
            quality=resize_pb2.ResizeQuality.RESIZE_QUALITY_GOOD,
            execution_id=execution_id,
        )

        # Execute direct gRPC call
        client = self.clients.get("resize")
        if not client:
            raise RuntimeError("Resize gRPC client not available")

        timeout = self.grpc_services["resize"]["timeout"]
        response = await client.ResizeImage(request, timeout=timeout)

        return {
            "output_path": response.result.output_image.object_key,
            "metadata": {
                "original_width": response.metadata.original_width,
                "original_height": response.metadata.original_height,
                "new_width": response.metadata.output_width,
                "new_height": response.metadata.output_height,
                "processing_time_ms": response.result.processing_time_seconds * 1000,
            },
        }

    async def _execute_ai_detection_step(
        self, step: Dict[str, Any], input_path: str, execution_id: str
    ) -> Dict[str, Any]:
        """Execute AI detection step via direct gRPC call"""
        parameters = step.get("parameters", {})

        # Create gRPC request
        request = ai_detection_pb2.DetectionRequest(
            input_image=common_pb2.ImageData(
                bucket="imageflow-files",
                object_key=input_path,
                content_type="image/jpeg",
            ),
            model_name=parameters.get("model_name", "yolo"),
            confidence_threshold=float(parameters.get("confidence_threshold", 0.5)),
            nms_threshold=float(parameters.get("nms_threshold", 0.4)),
            draw_boxes=parameters.get("draw_boxes", True),
            execution_id=execution_id,
        )

        # Execute direct gRPC call
        client = self.clients.get("ai_detection")
        if not client:
            raise RuntimeError("AI detection gRPC client not available")

        timeout = self.grpc_services["ai_detection"]["timeout"]
        response = await client.DetectObjects(request, timeout=timeout)

        # Extract metadata from gRPC response
        grpc_metadata = {}
        if hasattr(response.result, "metadata") and response.result.metadata:
            for key, value in response.result.metadata.items():
                grpc_metadata[key] = value

        return {
            "output_path": response.result.output_image.object_key,
            "metadata": {
                "detected_objects": len(response.detections),
                "detection_details": [
                    {
                        "class_name": det.class_name,
                        "confidence": det.confidence,
                        "bbox": {
                            "x1": det.bbox.x1,
                            "y1": det.bbox.y1,
                            "x2": det.bbox.x2,
                            "y2": det.bbox.y2,
                        },
                    }
                    for det in response.detections
                ],
                "processing_time_ms": response.result.processing_time_seconds * 1000,
                **grpc_metadata,  # Include the gRPC metadata containing json_output_file
            },
        }

    async def _execute_filter_step(
        self, step: Dict[str, Any], input_path: str, execution_id: str
    ) -> Dict[str, Any]:
        """Execute filter step via direct gRPC call"""
        parameters = step.get("parameters", {})

        # Create gRPC request
        request = filter_pb2.FilterRequest(
            input_image=common_pb2.ImageData(
                bucket="imageflow-files",
                object_key=input_path,
                content_type="image/jpeg",
            ),
            filter_type=self._get_filter_type_enum(
                parameters.get("filter_type", "gaussian")
            ),
            intensity=float(parameters.get("intensity", 1.0)),
            execution_id=execution_id,
        )

        # Execute direct gRPC call
        client = self.clients.get("filter")
        if not client:
            raise RuntimeError("Filter gRPC client not available")

        timeout = self.grpc_services["filter"]["timeout"]
        response = await client.ApplyFilter(request, timeout=timeout)

        return {
            "output_path": response.result.output_image.object_key,
            "metadata": {
                "filter_applied": parameters.get("filter_type", "gaussian"),
                "intensity": parameters.get("intensity", 1.0),
                "processing_time_ms": response.result.processing_time_seconds * 1000,
            },
        }

    def _get_filter_type_enum(self, filter_type_str: str):
        """Convert string filter type to protobuf enum"""
        filter_map = {
            "gaussian": filter_pb2.FilterType.FILTER_TYPE_GAUSSIAN,
            "blur": filter_pb2.FilterType.FILTER_TYPE_BLUR,
            "sharpen": filter_pb2.FilterType.FILTER_TYPE_SHARPEN,
            "brightness": filter_pb2.FilterType.FILTER_TYPE_BRIGHTNESS,
            "contrast": filter_pb2.FilterType.FILTER_TYPE_CONTRAST,
            "saturation": filter_pb2.FilterType.FILTER_TYPE_SATURATION,
        }
        return filter_map.get(
            filter_type_str.lower(), filter_pb2.FilterType.FILTER_TYPE_GAUSSIAN
        )

    def _resolve_step_dependencies(
        self, steps: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Resolve step dependencies and return execution order
        Groups parallel-executable steps together for optimization
        """
        # Build dependency graph
        step_map = {step["stepId"]: step for step in steps}
        dependencies = {}

        for step in steps:
            step_id = step["stepId"]
            step_deps = step.get("dependencies", [])
            dependencies[step_id] = step_deps

        # Topological sort with parallel grouping
        executed = set()
        execution_order = []

        while len(executed) < len(steps):
            # Find steps with no unexecuted dependencies
            ready_steps = []
            for step_id, deps in dependencies.items():
                if step_id not in executed:
                    if all(dep in executed for dep in deps):
                        ready_steps.append(step_map[step_id])

            if not ready_steps:
                # Circular dependency or error
                remaining_steps = [
                    step_map[step_id]
                    for step_id in dependencies.keys()
                    if step_id not in executed
                ]
                execution_order.append(remaining_steps)
                break

            execution_order.append(ready_steps)
            executed.update(step["stepId"] for step in ready_steps)

        return execution_order

    async def _send_progress_notification(
        self, execution_id: str, step_id: str, status: str, data: Dict[str, Any]
    ):
        """Send progress notification to Kafka"""
        try:
            notification = {
                "execution_id": execution_id,
                "step_id": step_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }

            await self.kafka_service.send_message("pipeline-progress", notification)

        except Exception as e:
            logger.warning(f"Failed to send progress notification: {e}")

    async def close(self):
        """Close gRPC connections"""
        for channel in self.channels.values():
            await channel.close()


# Global instance
_grpc_pipeline_executor = None


def get_grpc_pipeline_executor() -> GRPCPipelineExecutor:
    """Get global gRPC pipeline executor instance"""
    global _grpc_pipeline_executor
    if _grpc_pipeline_executor is None:
        _grpc_pipeline_executor = GRPCPipelineExecutor()
    return _grpc_pipeline_executor

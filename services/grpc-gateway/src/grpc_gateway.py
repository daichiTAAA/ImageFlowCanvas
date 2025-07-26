import sys
import os
import logging
import json
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import grpc
import uvicorn
from google.protobuf.json_format import MessageToDict, ParseDict

# Add generated proto path
sys.path.append("/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python")

from imageflow.v1 import resize_pb2
from imageflow.v1 import resize_pb2_grpc
from imageflow.v1 import ai_detection_pb2
from imageflow.v1 import ai_detection_pb2_grpc
from imageflow.v1 import filter_pb2
from imageflow.v1 import filter_pb2_grpc
from imageflow.v1 import camera_stream_pb2
from imageflow.v1 import camera_stream_pb2_grpc
from imageflow.v1 import common_pb2

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ImageFlow gRPC Gateway", version="1.0.0")


# gRPC client connections
class GRPCClients:
    def __init__(self):
        # Detect deployment environment and set appropriate default endpoints
        deployment_env = os.getenv("DEPLOYMENT_ENV", "nomad")  # nomad, k3s, docker

        # Set default endpoints based on environment
        if deployment_env == "k3s":
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
            camera_stream_default = (
                "camera-stream-grpc-service.image-processing.svc.cluster.local:9090"
            )
        elif deployment_env == "docker":
            # Docker Compose service names
            resize_default = "resize-grpc:9090"
            ai_detection_default = "ai-detection-grpc:9090"
            filter_default = "filter-grpc:9090"
            camera_stream_default = "camera-stream-grpc:9090"
        else:
            # Nomad with direct IP addressing
            nomad_ip = os.getenv("NOMAD_IP", "192.168.5.15")
            resize_default = f"{nomad_ip}:9092"
            ai_detection_default = f"{nomad_ip}:9091"
            filter_default = f"{nomad_ip}:9093"
            camera_stream_default = f"{nomad_ip}:9094"

        self.resize_endpoint = os.getenv("RESIZE_GRPC_ENDPOINT", resize_default)
        self.ai_detection_endpoint = os.getenv(
            "AI_DETECTION_GRPC_ENDPOINT", ai_detection_default
        )
        self.filter_endpoint = os.getenv("FILTER_GRPC_ENDPOINT", filter_default)
        self.camera_stream_endpoint = os.getenv(
            "CAMERA_STREAM_GRPC_ENDPOINT", camera_stream_default
        )

        logger.info(f"Deployment environment: {deployment_env}")
        logger.info(f"Resize service: {self.resize_endpoint}")
        logger.info(f"AI Detection service: {self.ai_detection_endpoint}")
        logger.info(f"Filter service: {self.filter_endpoint}")
        logger.info(f"Camera Stream service: {self.camera_stream_endpoint}")

    def get_resize_client(self):
        channel = grpc.insecure_channel(self.resize_endpoint)
        return resize_pb2_grpc.ResizeServiceStub(channel)

    def get_ai_detection_client(self):
        channel = grpc.insecure_channel(self.ai_detection_endpoint)
        return ai_detection_pb2_grpc.AIDetectionServiceStub(channel)

    def get_filter_client(self):
        channel = grpc.insecure_channel(self.filter_endpoint)
        return filter_pb2_grpc.FilterServiceStub(channel)

    def get_camera_stream_client(self):
        channel = grpc.insecure_channel(self.camera_stream_endpoint)
        return camera_stream_pb2_grpc.CameraStreamProcessorStub(channel)


grpc_clients = GRPCClients()


# Pydantic models for HTTP requests
class ImageDataModel(BaseModel):
    bucket: str
    object_key: str
    content_type: str = ""
    size_bytes: int = 0
    width: int = 0
    height: int = 0


class ResizeRequestModel(BaseModel):
    input_image: ImageDataModel
    target_width: int = 800
    target_height: int = 600
    maintain_aspect_ratio: bool = True
    quality: str = "RESIZE_QUALITY_GOOD"
    execution_id: str


class DetectionRequestModel(BaseModel):
    input_image: ImageDataModel
    model_name: str = "yolo"
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    draw_boxes: bool = True
    execution_id: str


class FilterRequestModel(BaseModel):
    input_image: ImageDataModel
    filter_type: str = "FILTER_TYPE_BLUR"
    intensity: float = 1.0
    parameters: Dict[str, str] = {}
    execution_id: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "grpc-gateway"}


@app.post("/v1/resize")
async def resize_image(request: ResizeRequestModel):
    """Resize image via gRPC service"""
    try:
        logger.info(f"Gateway: Processing resize request for {request.execution_id}")

        # Convert HTTP request to gRPC request
        grpc_request = resize_pb2.ResizeRequest()
        grpc_request.input_image.bucket = request.input_image.bucket
        grpc_request.input_image.object_key = request.input_image.object_key
        grpc_request.input_image.content_type = request.input_image.content_type
        grpc_request.target_width = request.target_width
        grpc_request.target_height = request.target_height
        grpc_request.maintain_aspect_ratio = request.maintain_aspect_ratio
        grpc_request.execution_id = request.execution_id

        # Map quality string to enum
        quality_map = {
            "RESIZE_QUALITY_FAST": resize_pb2.RESIZE_QUALITY_FAST,
            "RESIZE_QUALITY_GOOD": resize_pb2.RESIZE_QUALITY_GOOD,
            "RESIZE_QUALITY_BEST": resize_pb2.RESIZE_QUALITY_BEST,
        }
        grpc_request.quality = quality_map.get(
            request.quality, resize_pb2.RESIZE_QUALITY_GOOD
        )

        # Call gRPC service
        client = grpc_clients.get_resize_client()
        grpc_response = client.ResizeImage(grpc_request)

        # Convert gRPC response to HTTP response
        response_dict = MessageToDict(grpc_response, preserving_proto_field_name=True)

        logger.info(f"Gateway: Resize completed for {request.execution_id}")
        return response_dict

    except grpc.RpcError as e:
        logger.error(f"gRPC error in resize: {e}")
        raise HTTPException(
            status_code=500, detail=f"gRPC service error: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in resize gateway: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/detect")
async def detect_objects(request: DetectionRequestModel):
    """Detect objects via gRPC service"""
    try:
        logger.info(f"Gateway: Processing detection request for {request.execution_id}")

        # Convert HTTP request to gRPC request
        grpc_request = ai_detection_pb2.DetectionRequest()
        grpc_request.input_image.bucket = request.input_image.bucket
        grpc_request.input_image.object_key = request.input_image.object_key
        grpc_request.input_image.content_type = request.input_image.content_type
        grpc_request.model_name = request.model_name
        grpc_request.confidence_threshold = request.confidence_threshold
        grpc_request.nms_threshold = request.nms_threshold
        grpc_request.draw_boxes = request.draw_boxes
        grpc_request.execution_id = request.execution_id

        # Call gRPC service
        client = grpc_clients.get_ai_detection_client()
        grpc_response = client.DetectObjects(grpc_request)

        # Convert gRPC response to HTTP response
        response_dict = MessageToDict(grpc_response, preserving_proto_field_name=True)

        logger.info(f"Gateway: Detection completed for {request.execution_id}")
        return response_dict

    except grpc.RpcError as e:
        logger.error(f"gRPC error in detection: {e}")
        raise HTTPException(
            status_code=500, detail=f"gRPC service error: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in detection gateway: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/filter")
async def apply_filter(request: FilterRequestModel):
    """Apply filter via gRPC service"""
    try:
        logger.info(f"Gateway: Processing filter request for {request.execution_id}")

        # Convert HTTP request to gRPC request
        grpc_request = filter_pb2.FilterRequest()
        grpc_request.input_image.bucket = request.input_image.bucket
        grpc_request.input_image.object_key = request.input_image.object_key
        grpc_request.input_image.content_type = request.input_image.content_type
        grpc_request.intensity = request.intensity
        grpc_request.execution_id = request.execution_id

        # Map filter type string to enum
        filter_type_map = {
            "FILTER_TYPE_BLUR": filter_pb2.FILTER_TYPE_BLUR,
            "FILTER_TYPE_GAUSSIAN": filter_pb2.FILTER_TYPE_GAUSSIAN,
            "FILTER_TYPE_SHARPEN": filter_pb2.FILTER_TYPE_SHARPEN,
            "FILTER_TYPE_BRIGHTNESS": filter_pb2.FILTER_TYPE_BRIGHTNESS,
            "FILTER_TYPE_CONTRAST": filter_pb2.FILTER_TYPE_CONTRAST,
            "FILTER_TYPE_SATURATION": filter_pb2.FILTER_TYPE_SATURATION,
        }
        grpc_request.filter_type = filter_type_map.get(
            request.filter_type, filter_pb2.FILTER_TYPE_BLUR
        )

        # Add parameters
        for key, value in request.parameters.items():
            grpc_request.parameters[key] = value

        # Call gRPC service
        client = grpc_clients.get_filter_client()
        grpc_response = client.ApplyFilter(grpc_request)

        # Convert gRPC response to HTTP response
        response_dict = MessageToDict(grpc_response, preserving_proto_field_name=True)

        logger.info(f"Gateway: Filter completed for {request.execution_id}")
        return response_dict

    except grpc.RpcError as e:
        logger.error(f"gRPC error in filter: {e}")
        raise HTTPException(
            status_code=500, detail=f"gRPC service error: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in filter gateway: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/health/resize")
async def health_resize():
    """Check resize service health"""
    try:
        client = grpc_clients.get_resize_client()
        request = common_pb2.HealthCheckRequest(service="resize")
        response = client.Health(request)
        return {"service": "resize", "status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Resize service unhealthy: {e}")


@app.get("/v1/health/detection")
async def health_detection():
    """Check AI detection service health"""
    try:
        client = grpc_clients.get_ai_detection_client()
        request = common_pb2.HealthCheckRequest(service="detection")
        response = client.Health(request)
        return {"service": "detection", "status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Detection service unhealthy: {e}")


@app.get("/v1/health/camera_stream")
async def health_camera_stream():
    """Check camera stream service health"""
    try:
        client = grpc_clients.get_camera_stream_client()
        request = common_pb2.HealthCheckRequest(service="camera_stream")
        response = client.Health(request)
        return {"service": "camera_stream", "status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Camera stream service unhealthy: {e}"
        )


if __name__ == "__main__":
    port = int(os.getenv("HTTP_PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting gRPC Gateway on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

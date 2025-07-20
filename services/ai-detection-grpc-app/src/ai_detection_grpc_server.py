import sys
import os
import time
import logging
import json
from concurrent import futures
from datetime import datetime, timezone

import grpc
from minio import Minio
import cv2
import numpy as np
import requests
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto path
sys.path.append('/app/generated/python')
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')

from imageflow.v1 import ai_detection_pb2
from imageflow.v1 import ai_detection_pb2_grpc
from imageflow.v1 import common_pb2
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIDetectionServiceImplementation(ai_detection_pb2_grpc.AIDetectionServiceServicer):
    def __init__(self):
        # MinIO client setup
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        # Create MinIO client pool for connection reuse
        self._create_minio_client()
        
        # Triton server endpoint
        self.triton_url = os.getenv("TRITON_GRPC_URL", "triton-service:8001")
        
        # Performance optimization: pre-warm services
        self._warm_up()
        
        logger.info(f"Initialized optimized AI Detection Service with Triton: {self.triton_url}")

    def _create_minio_client(self):
        """Create MinIO client with optimized settings"""
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False
        )
        
    def _warm_up(self):
        """Pre-warm AI detection and OpenCV for better performance"""
        try:
            # Create a small dummy image to warm up OpenCV and detection pipeline
            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            cv2.resize(dummy, (100, 100))
            # Warm up detection pipeline with dummy data
            self._perform_object_detection(dummy, "yolo", 0.5, 0.4)
            logger.info("AI Detection service warmed up successfully")
        except Exception as e:
            logger.warning(f"Warm-up failed: {e}")
            
    def _health_check(self):
        """Internal health check method"""
        try:
            # Test MinIO connection
            self.minio_client.list_buckets()
            # Test OpenCV functionality
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.resize(test_img, (50, 50))
            # Test detection pipeline
            self._perform_object_detection(test_img, "yolo", 0.5, 0.4)
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def DetectObjects(self, request, context):
        """Handle object detection request"""
        start_time = time.time()
        logger.info(f"Processing AI detection request for execution_id: {request.execution_id}")
        
        try:
            # Download image from MinIO
            local_input = f"/tmp/input_{request.execution_id}"
            local_output = f"/tmp/output_{request.execution_id}"
            
            logger.info(f"Downloading {request.input_image.object_key} from bucket {request.input_image.bucket}")
            self.minio_client.fget_object(
                request.input_image.bucket, 
                request.input_image.object_key, 
                local_input
            )
            
            # Load image
            image = cv2.imread(local_input)
            if image is None:
                raise ValueError(f"Could not read input image: {request.input_image.object_key}")
            
            original_height, original_width = image.shape[:2]
            logger.info(f"Processing image size: {original_width}x{original_height}")
            
            # Perform object detection (mock implementation for now)
            detections = self._perform_object_detection(
                image, 
                request.model_name,
                request.confidence_threshold,
                request.nms_threshold
            )
            
            inference_time = time.time() - start_time
            
            # Draw bounding boxes if requested
            output_image = image.copy()
            if request.draw_boxes and detections:
                output_image = self._draw_bounding_boxes(output_image, detections)
            
            # Save output image
            output_path = request.input_image.object_key.replace('.png', '_detected.png').replace('.jpg', '_detected.jpg')
            if not output_path.endswith(('.png', '.jpg', '.jpeg')):
                output_path += '.jpg'
                
            cv2.imwrite(local_output, output_image)
            
            # Upload to MinIO
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                self.minio_client.make_bucket(request.input_image.bucket)
                
            self.minio_client.fput_object(
                request.input_image.bucket,
                output_path,
                local_output
            )
            logger.info(f"Uploaded detection result to {output_path}")
            
            # Save detection metadata
            metadata_path = output_path.replace('.png', '_metadata.json').replace('.jpg', '_metadata.json')
            detection_data = {
                "detections": [
                    {
                        "class_name": det["class_name"],
                        "confidence": det["confidence"],
                        "bbox": det["bbox"],
                        "class_id": det["class_id"]
                    } for det in detections
                ],
                "model_name": request.model_name,
                "confidence_threshold": request.confidence_threshold,
                "total_detections": len(detections)
            }
            
            with open(f"/tmp/metadata_{request.execution_id}.json", "w") as f:
                json.dump(detection_data, f)
            
            self.minio_client.fput_object(
                request.input_image.bucket,
                metadata_path,
                f"/tmp/metadata_{request.execution_id}.json"
            )
            
            # Cleanup local files
            for temp_file in [local_input, local_output, f"/tmp/metadata_{request.execution_id}.json"]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            processing_time = time.time() - start_time
            
            # Create response
            response = ai_detection_pb2.DetectionResponse()
            
            # Set processing result
            response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
            response.result.message = f"Object detection completed. Found {len(detections)} objects."
            
            # Set output image info
            response.result.output_image.bucket = request.input_image.bucket
            response.result.output_image.object_key = output_path
            response.result.output_image.content_type = "image/jpeg" if output_path.endswith('.jpg') else "image/png"
            response.result.output_image.width = original_width
            response.result.output_image.height = original_height
            
            # Set timestamp
            now = Timestamp()
            now.FromDatetime(datetime.now(timezone.utc))
            response.result.processed_at.CopyFrom(now)
            response.result.processing_time_seconds = processing_time
            
            # Add detections
            for detection in detections:
                det_proto = response.detections.add()
                det_proto.class_name = detection["class_name"]
                det_proto.confidence = detection["confidence"]
                det_proto.class_id = detection["class_id"]
                det_proto.bbox.x1 = detection["bbox"]["x1"]
                det_proto.bbox.y1 = detection["bbox"]["y1"]
                det_proto.bbox.x2 = detection["bbox"]["x2"]
                det_proto.bbox.y2 = detection["bbox"]["y2"]
            
            # Set metadata
            response.metadata.model_name = request.model_name
            response.metadata.model_version = "v1.0"
            response.metadata.confidence_threshold = request.confidence_threshold
            response.metadata.nms_threshold = request.nms_threshold
            response.metadata.total_detections = len(detections)
            response.metadata.inference_time_ms = inference_time * 1000
            response.metadata.nms_time_ms = 0  # Mock value
            
            logger.info(f"AI detection completed in {processing_time:.2f}s with {len(detections)} detections")
            return response
            
        except Exception as e:
            logger.error(f"Error processing AI detection request: {str(e)}")
            
            # Return error response
            response = ai_detection_pb2.DetectionResponse()
            response.result.status = common_pb2.PROCESSING_STATUS_FAILED
            response.result.message = f"AI detection failed: {str(e)}"
            response.result.processing_time_seconds = time.time() - start_time
            
            return response

    def _perform_object_detection(self, image, model_name, confidence_threshold, nms_threshold):
        """Mock object detection implementation"""
        # This is a simplified mock implementation
        # In a real scenario, this would call Triton Inference Server
        
        logger.info(f"Running {model_name} detection with confidence threshold {confidence_threshold}")
        
        # Mock detection results
        detections = [
            {
                "class_name": "person",
                "confidence": 0.85,
                "class_id": 0,
                "bbox": {
                    "x1": 100.0,
                    "y1": 50.0,
                    "x2": 200.0,
                    "y2": 300.0
                }
            },
            {
                "class_name": "car",
                "confidence": 0.72,
                "class_id": 2,
                "bbox": {
                    "x1": 300.0,
                    "y1": 200.0,
                    "x2": 500.0,
                    "y2": 350.0
                }
            }
        ]
        
        # Filter by confidence threshold
        filtered_detections = [
            det for det in detections 
            if det["confidence"] >= confidence_threshold
        ]
        
        return filtered_detections

    def _draw_bounding_boxes(self, image, detections):
        """Draw bounding boxes on image"""
        colors = {
            "person": (0, 255, 0),  # Green
            "car": (255, 0, 0),     # Blue
            "default": (0, 0, 255)  # Red
        }
        
        for detection in detections:
            bbox = detection["bbox"]
            class_name = detection["class_name"]
            confidence = detection["confidence"]
            
            color = colors.get(class_name, colors["default"])
            
            # Draw rectangle
            cv2.rectangle(
                image,
                (int(bbox["x1"]), int(bbox["y1"])),
                (int(bbox["x2"]), int(bbox["y2"])),
                color,
                2
            )
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(
                image,
                label,
                (int(bbox["x1"]), int(bbox["y1"]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )
        
        return image

    def Health(self, request, context):
        """Health check endpoint with actual service verification"""
        response = common_pb2.HealthCheckResponse()
        
        if self._health_check():
            response.status = common_pb2.HealthCheckResponse.SERVING
            logger.debug("AI Detection health check passed")
        else:
            response.status = common_pb2.HealthCheckResponse.NOT_SERVING
            logger.warning("AI Detection health check failed")
            
        return response


class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
    """Standard gRPC health check service implementation"""
    
    def __init__(self, ai_detection_service):
        self.ai_detection_service = ai_detection_service
    
    def Check(self, request, context):
        """Standard gRPC health check implementation"""
        response = health_pb2.HealthCheckResponse()
        
        if self.ai_detection_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
            logger.debug("AI Detection health check passed")
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
            logger.warning("AI Detection health check failed")
            
        return response
    
    def Watch(self, request, context):
        """Health check watch implementation (streaming)"""
        # For simplicity, just return current status
        response = health_pb2.HealthCheckResponse()
        
        if self.ai_detection_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
            
        yield response

def serve():
    """Start the gRPC server with optimized configuration"""
    port = os.getenv("GRPC_PORT", "9090")
    
    # Optimize thread pool for AI workloads
    max_workers = int(os.getenv("GRPC_MAX_WORKERS", "15"))
    
    # Configure server options for better performance
    server_options = [
        ('grpc.keepalive_time_ms', 30000),
        ('grpc.keepalive_timeout_ms', 5000),
        ('grpc.keepalive_permit_without_calls', True),
        ('grpc.http2.max_pings_without_data', 0),
        ('grpc.http2.min_time_between_pings_ms', 10000),
        ('grpc.http2.min_ping_interval_without_data_ms', 5000),
        ('grpc.max_connection_idle_ms', 300000),
        ('grpc.max_connection_age_ms', 600000),
    ]
    
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers), 
        options=server_options
    )
    
    # Create service instances
    ai_detection_service = AIDetectionServiceImplementation()
    health_service = HealthServiceImplementation(ai_detection_service)
    
    # Add services to server
    ai_detection_pb2_grpc.add_AIDetectionServiceServicer_to_server(
        ai_detection_service, server
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_service, server)
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting gRPC AI Detection Service on {listen_addr}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)

if __name__ == '__main__':
    serve()
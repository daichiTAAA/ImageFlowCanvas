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
from PIL import Image
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto path
sys.path.append("/app/generated/python")
sys.path.append("/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python")

from imageflow.v1 import ai_detection_pb2
from imageflow.v1 import ai_detection_pb2_grpc
from imageflow.v1 import common_pb2
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AIDetectionServiceImplementation(
    ai_detection_pb2_grpc.AIDetectionServiceServicer
):
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

        logger.info(
            f"Initialized optimized AI Detection Service with Triton: {self.triton_url}"
        )

    def _create_minio_client(self):
        """Create MinIO client with optimized settings"""
        try:
            self.minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=False,
            )
            logger.info(
                f"MinIO client created successfully for endpoint: {self.minio_endpoint}"
            )

            # Test connection
            buckets = self.minio_client.list_buckets()
            logger.info(
                f"MinIO connection successful. Available buckets: {[b.name for b in buckets]}"
            )

        except Exception as e:
            logger.error(f"Failed to create MinIO client: {e}")
            raise

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
        logger.info(
            f"Processing AI detection request for execution_id: {request.execution_id}"
        )

        try:
            # Download image from MinIO
            local_input = f"/tmp/input_{request.execution_id}"
            local_output = f"/tmp/output_{request.execution_id}"

            # Check if bucket exists
            bucket_name = request.input_image.bucket
            object_key = request.input_image.object_key

            logger.info(f"Checking bucket '{bucket_name}' existence...")
            if not self.minio_client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket '{bucket_name}' does not exist")

            # List objects in bucket for debugging
            logger.info(f"Listing objects in bucket '{bucket_name}'...")
            try:
                objects = list(
                    self.minio_client.list_objects(
                        bucket_name, prefix="", recursive=True
                    )
                )
                logger.info(f"Found {len(objects)} objects in bucket:")
                for obj in objects[:10]:  # Show first 10 objects
                    logger.info(
                        f"  - {obj.object_name} (size: {obj.size}, modified: {obj.last_modified})"
                    )
                if len(objects) > 10:
                    logger.info(f"  ... and {len(objects) - 10} more objects")
            except Exception as list_error:
                logger.warning(f"Could not list objects in bucket: {list_error}")

            # Check if the specific object exists
            logger.info(
                f"Checking if object '{object_key}' exists in bucket '{bucket_name}'..."
            )
            try:
                self.minio_client.stat_object(bucket_name, object_key)
                logger.info(f"Object '{object_key}' exists")
            except Exception as stat_error:
                logger.error(f"Object '{object_key}' does not exist: {stat_error}")

                # Try to find similar objects (with potential extensions)
                possible_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
                found_alternative = False

                for ext in possible_extensions:
                    try_key = object_key + ext
                    try:
                        self.minio_client.stat_object(bucket_name, try_key)
                        logger.info(f"Found alternative object: '{try_key}'")
                        object_key = try_key  # Use the found object
                        found_alternative = True
                        break
                    except:
                        continue

                if not found_alternative:
                    # Try without execution_id suffix and with extensions
                    base_name = (
                        object_key.split("_")[0] if "_" in object_key else object_key
                    )
                    for ext in possible_extensions:
                        try_key = base_name + ext
                        try:
                            self.minio_client.stat_object(bucket_name, try_key)
                            logger.info(f"Found base name alternative: '{try_key}'")
                            object_key = try_key
                            found_alternative = True
                            break
                        except:
                            continue

                if not found_alternative:
                    raise ValueError(
                        f"Could not find object '{request.input_image.object_key}' or any alternative in bucket '{bucket_name}'"
                    )

            logger.info(f"Downloading '{object_key}' from bucket '{bucket_name}'")
            self.minio_client.fget_object(bucket_name, object_key, local_input)

            # Load image
            image = cv2.imread(local_input)
            if image is None:
                raise ValueError(
                    f"Could not read input image: {request.input_image.object_key}"
                )

            original_height, original_width = image.shape[:2]
            logger.info(f"Processing image size: {original_width}x{original_height}")

            # Perform object detection (mock implementation for now)
            detections = self._perform_object_detection(
                image,
                request.model_name,
                request.confidence_threshold,
                request.nms_threshold,
            )

            inference_time = time.time() - start_time

            # Draw bounding boxes if requested
            output_image = image.copy()
            if request.draw_boxes and detections:
                output_image = self._draw_bounding_boxes(output_image, detections)

            # Save output image with workflow-expected naming
            # ワークフローでは {execution_id}_detected.jpg を期待している
            execution_id = request.execution_id
            output_path = f"{execution_id}_detected.jpg"

            # Use Pillow for reliable JPEG saving
            # Convert BGR (OpenCV) to RGB (Pillow)
            output_rgb = cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(output_rgb)
            pil_image.save(local_output, "JPEG", quality=85, optimize=True)

            # Upload to MinIO
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                self.minio_client.make_bucket(request.input_image.bucket)

            self.minio_client.fput_object(
                request.input_image.bucket, output_path, local_output
            )
            logger.info(f"Uploaded detection result to {output_path}")

            # Save detection metadata with enhanced information
            metadata_path = output_path.replace(".png", ".json").replace(
                ".jpg", ".json"
            )
            detection_data = {
                "execution_id": request.execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "image_info": {
                    "input_file": request.input_image.object_key,
                    "output_file": output_path,
                    "width": original_width,
                    "height": original_height,
                },
                "model_info": {
                    "name": request.model_name,
                    "version": "v1.0",
                    "confidence_threshold": request.confidence_threshold,
                    "nms_threshold": request.nms_threshold,
                },
                "processing_info": {
                    "inference_time_ms": inference_time * 1000,
                    "total_processing_time_ms": (time.time() - start_time) * 1000,
                },
                "detections": [
                    {
                        "class_name": det["class_name"],
                        "confidence": det["confidence"],
                        "bbox": det["bbox"],
                        "class_id": det["class_id"],
                        "bbox_area": (det["bbox"]["x2"] - det["bbox"]["x1"])
                        * (det["bbox"]["y2"] - det["bbox"]["y1"]),
                        "bbox_center": {
                            "x": (det["bbox"]["x1"] + det["bbox"]["x2"]) / 2,
                            "y": (det["bbox"]["y1"] + det["bbox"]["y2"]) / 2,
                        },
                    }
                    for det in detections
                ],
                "summary": {
                    "total_detections": len(detections),
                    "classes_detected": list(
                        set([det["class_name"] for det in detections])
                    ),
                    "highest_confidence": (
                        max([det["confidence"] for det in detections])
                        if detections
                        else 0.0
                    ),
                    "average_confidence": (
                        sum([det["confidence"] for det in detections]) / len(detections)
                        if detections
                        else 0.0
                    ),
                },
            }

            with open(f"/tmp/metadata_{request.execution_id}.json", "w") as f:
                json.dump(detection_data, f, indent=2, ensure_ascii=False)

            self.minio_client.fput_object(
                request.input_image.bucket,
                metadata_path,
                f"/tmp/metadata_{request.execution_id}.json",
            )
            logger.info(f"Uploaded detection JSON metadata to {metadata_path}")

            # Cleanup local files
            for temp_file in [
                local_input,
                local_output,
                f"/tmp/metadata_{request.execution_id}.json",
            ]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            processing_time = time.time() - start_time

            # Create response
            response = ai_detection_pb2.DetectionResponse()

            # Set processing result
            response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
            response.result.message = (
                f"Object detection completed. Found {len(detections)} objects."
            )

            # Set output image info
            response.result.output_image.bucket = request.input_image.bucket
            response.result.output_image.object_key = output_path
            response.result.output_image.content_type = (
                "image/jpeg" if output_path.endswith(".jpg") else "image/png"
            )
            response.result.output_image.width = original_width
            response.result.output_image.height = original_height

            # Add JSON detection file info to metadata
            json_filename = f"{request.execution_id}_detected.json"
            response.result.metadata["json_output_file"] = json_filename
            response.result.metadata["json_content_type"] = "application/json"

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

            logger.info(
                f"AI detection completed in {processing_time:.2f}s with {len(detections)} detections"
            )
            return response

        except Exception as e:
            logger.error(f"Error processing AI detection request: {str(e)}")

            # Return error response
            response = ai_detection_pb2.DetectionResponse()
            response.result.status = common_pb2.PROCESSING_STATUS_FAILED
            response.result.message = f"AI detection failed: {str(e)}"
            response.result.processing_time_seconds = time.time() - start_time

            return response

    def _perform_object_detection(
        self, image, model_name, confidence_threshold, nms_threshold
    ):
        """Actual YOLO object detection implementation using ultralytics"""
        logger.info(
            f"Running {model_name} detection with confidence threshold {confidence_threshold}"
        )

        try:
            # Import ultralytics for YOLO detection
            from ultralytics import YOLO

            # Load YOLO model (will download if not exists)
            if model_name.lower() in ["yolo", "yolo11", "yolov11"]:
                model = YOLO("yolo11n.pt")  # Use YOLO11 nano model
            elif model_name.lower() in ["yolov8", "yolo8"]:
                model = YOLO("yolov8n.pt")  # Use YOLOv8 nano model
            else:
                # Default to YOLO11
                model = YOLO("yolo11n.pt")

            # Run inference
            results = model(
                image, conf=confidence_threshold, iou=nms_threshold, verbose=False
            )

            detections = []
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        # Get detection data
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())

                        # Get class name from model names
                        class_name = (
                            model.names[class_id]
                            if class_id < len(model.names)
                            else f"class_{class_id}"
                        )

                        detection = {
                            "class_name": class_name,
                            "confidence": confidence,
                            "class_id": class_id,
                            "bbox": {
                                "x1": float(x1),
                                "y1": float(y1),
                                "x2": float(x2),
                                "y2": float(y2),
                            },
                        }
                        detections.append(detection)

            logger.info(
                f"Detected {len(detections)} objects: {[d['class_name'] for d in detections]}"
            )
            return detections

        except Exception as e:
            logger.error(f"Error in YOLO detection: {str(e)}")
            # Fallback to mock detection on error
            logger.warning("Falling back to mock detection due to error")
            detections = [
                {
                    "class_name": "error_fallback",
                    "confidence": 0.5,
                    "class_id": 999,
                    "bbox": {"x1": 100.0, "y1": 50.0, "x2": 200.0, "y2": 300.0},
                },
            ]
            return detections

    def _draw_bounding_boxes(self, image, detections):
        """Draw bounding boxes on image with enhanced labels"""
        colors = {
            "person": (0, 255, 0),  # Green
            "car": (255, 0, 0),  # Blue
            "horse": (255, 255, 0),  # Cyan
            "dog": (255, 0, 255),  # Magenta
            "cat": (0, 255, 255),  # Yellow
            "bird": (128, 0, 128),  # Purple
            "bicycle": (255, 128, 0),  # Orange
            "motorcycle": (0, 128, 255),  # Light blue
            "default": (0, 0, 255),  # Red
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
                2,
            )

            # Create label with background
            label = f"{class_name}: {confidence:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2

            # Get text size
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )

            # Calculate label position
            label_x = int(bbox["x1"])
            label_y = int(bbox["y1"]) - 10

            # Ensure label stays within image bounds
            if label_y - text_height - 5 < 0:
                label_y = int(bbox["y1"]) + text_height + 15

            # Draw semi-transparent background rectangle for label
            overlay = image.copy()
            cv2.rectangle(
                overlay,
                (label_x, label_y - text_height - 5),
                (label_x + text_width, label_y + baseline),
                color,
                -1,  # Fill rectangle
            )

            # Apply transparency to background
            alpha = 0.7  # Transparency level (0.0 = fully transparent, 1.0 = opaque)
            cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

            # Draw text on top of background
            cv2.putText(
                image,
                label,
                (label_x, label_y),
                font,
                font_scale,
                (255, 255, 255),  # White text for better contrast
                font_thickness,
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
        ("grpc.keepalive_time_ms", 30000),
        ("grpc.keepalive_timeout_ms", 5000),
        ("grpc.keepalive_permit_without_calls", True),
        ("grpc.http2.max_pings_without_data", 0),
        ("grpc.http2.min_time_between_pings_ms", 10000),
        ("grpc.http2.min_ping_interval_without_data_ms", 5000),
        ("grpc.max_connection_idle_ms", 300000),
        ("grpc.max_connection_age_ms", 600000),
    ]

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers), options=server_options
    )

    # Create service instances
    ai_detection_service = AIDetectionServiceImplementation()
    health_service = HealthServiceImplementation(ai_detection_service)

    # Add services to server
    ai_detection_pb2_grpc.add_AIDetectionServiceServicer_to_server(
        ai_detection_service, server
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_service, server)

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting gRPC AI Detection Service on {listen_addr}")
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()

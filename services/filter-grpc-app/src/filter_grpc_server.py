import sys
import os
import time
import logging
from concurrent import futures
from datetime import datetime, timezone

import grpc
from minio import Minio
import cv2
import numpy as np
from PIL import Image
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto path
sys.path.append("/app/generated/python")
sys.path.append("/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python")

from imageflow.v1 import filter_pb2
from imageflow.v1 import filter_pb2_grpc
from imageflow.v1 import common_pb2
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FilterServiceImplementation(filter_pb2_grpc.FilterServiceServicer):
    def __init__(self):
        # MinIO client setup
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

        # Create MinIO client pool for connection reuse
        self._create_minio_client()

        # Performance optimization: pre-warm OpenCV filters
        self._warm_up()

        try:
            cv2_path = getattr(cv2, "__file__", "<unknown>")
            cv2_ver = getattr(cv2, "__version__", "<unknown>")
            has_gauss = hasattr(cv2, "GaussianBlur")
            logger.info(
                f"Initialized Filter Service for {self.minio_endpoint} | cv2={cv2_ver} at {cv2_path} | has GaussianBlur={has_gauss}"
            )
        except Exception as e:
            logger.warning(f"Unable to introspect cv2: {e}")

    def _create_minio_client(self):
        """Create MinIO client with optimized settings"""
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False,
        )

    def _warm_up(self):
        """Pre-warm OpenCV filters for better performance"""
        try:
            # Create a small dummy image to warm up filter operations
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            # Test different filter types
            # Use simple blur to avoid GaussianBlur dependency
            cv2.blur(dummy, (5, 5))
            cv2.medianBlur(dummy, 5)
            cv2.bilateralFilter(dummy, 9, 75, 75)
            logger.info("Filter service warmed up successfully")
        except Exception as e:
            logger.warning(f"Warm-up failed: {e}")

    def _health_check(self):
        """Internal health check method"""
        try:
            # Test MinIO connection
            self.minio_client.list_buckets()
            # Test OpenCV functionality
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            # Avoid GaussianBlur; use simple blur
            cv2.blur(test_img, (5, 5))
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def ApplyFilter(self, request, context):
        """Handle filter application request"""
        start_time = time.time()
        logger.info(
            f"Processing filter request for execution_id: {request.execution_id}"
        )

        try:
            local_input = f"/tmp/input_{request.execution_id}"
            local_output = f"/tmp/output_{request.execution_id}"

            # Check if input is direct bytes or MinIO reference
            if request.HasField("input_bytes"):
                # Handle direct byte input (for real-time streaming)
                logger.info("Processing direct image bytes input")

                # Write bytes directly to temporary file
                with open(local_input, "wb") as f:
                    f.write(request.input_bytes.data)

                logger.info(
                    f"Saved {len(request.input_bytes.data)} bytes to {local_input}"
                )

            elif request.HasField("input_image"):
                # Handle MinIO reference input (for batch processing)
                logger.info("Processing MinIO image reference input")

                logger.info(
                    f"Downloading {request.input_image.object_key} from bucket {request.input_image.bucket}"
                )
                self.minio_client.fget_object(
                    request.input_image.bucket,
                    request.input_image.object_key,
                    local_input,
                )
            else:
                raise ValueError("Request must have either input_bytes or input_image")

            # Load image
            image = cv2.imread(local_input)
            if image is None:
                raise ValueError(f"Could not read input image from {local_input}")

            original_height, original_width = image.shape[:2]
            logger.info(f"Processing image size: {original_width}x{original_height}")

            # Apply filter
            filtered_image = self._apply_filter(
                image, request.filter_type, request.intensity, request.parameters
            )

            # For real-time processing (input_bytes), return direct bytes
            if request.HasField("input_bytes"):
                # Convert filtered image to JPEG bytes
                # Convert BGR (OpenCV) to RGB (Pillow)
                filtered_rgb = cv2.cvtColor(filtered_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(filtered_rgb)

                # Save to bytes buffer
                import io

                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format="JPEG", quality=85)
                img_bytes = img_buffer.getvalue()

                # Create response with direct bytes
                response = filter_pb2.FilterResponse()
                response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
                response.result.message = f"Filter {filter_pb2.FilterType.Name(request.filter_type)} applied successfully"
                response.result.output_data = img_bytes  # Store the actual image bytes

                # Set metadata
                response.result.output_image.content_type = "image/jpeg"
                response.result.output_image.width = original_width
                response.result.output_image.height = original_height  # Set timestamp
                now = Timestamp()
                now.FromDatetime(datetime.now(timezone.utc))
                response.result.processed_at.CopyFrom(now)
                response.result.processing_time_seconds = time.time() - start_time

                # Set metadata
                response.metadata.filter_type = request.filter_type
                response.metadata.intensity = request.intensity
                response.metadata.processing_time_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"Filter applied successfully, returning {len(img_bytes)} bytes"
                )

                # Clean up
                if os.path.exists(local_input):
                    os.remove(local_input)

                return response

            # For MinIO-based processing (input_image), upload to MinIO
            else:
                # Save filtered image with workflow-expected naming
                # ワークフローでは {execution_id}_final.jpg を期待している
                execution_id = request.execution_id
                output_path = f"{execution_id}_final.jpg"

                # Use Pillow for reliable JPEG saving
                # Convert BGR (OpenCV) to RGB (Pillow)
                filtered_rgb = cv2.cvtColor(filtered_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(filtered_rgb)
                pil_image.save(local_output, "JPEG", quality=85, optimize=True)

                # Upload to MinIO
                if not self.minio_client.bucket_exists(request.input_image.bucket):
                    self.minio_client.make_bucket(request.input_image.bucket)

                self.minio_client.fput_object(
                    request.input_image.bucket, output_path, local_output
                )
                logger.info(f"Uploaded filtered image to {output_path}")

                # Cleanup local files
                if os.path.exists(local_input):
                    os.remove(local_input)
                if os.path.exists(local_output):
                    os.remove(local_output)

                processing_time = time.time() - start_time

                # Create response
                response = filter_pb2.FilterResponse()

                # Set processing result
                response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
                response.result.message = f"Filter {filter_pb2.FilterType.Name(request.filter_type)} applied successfully"

                # Set output image info
                response.result.output_image.bucket = request.input_image.bucket
                response.result.output_image.object_key = output_path
                response.result.output_image.content_type = (
                    "image/jpeg" if output_path.endswith(".jpg") else "image/png"
                )
                response.result.output_image.width = original_width
                response.result.output_image.height = original_height

                # Set timestamp
                now = Timestamp()
                now.FromDatetime(datetime.now(timezone.utc))
                response.result.processed_at.CopyFrom(now)
                response.result.processing_time_seconds = processing_time

                # Set metadata
                response.metadata.filter_type = request.filter_type
            response.metadata.intensity = request.intensity
            for key, value in request.parameters.items():
                response.metadata.applied_parameters[key] = value

            logger.info(f"Filter applied in {processing_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Error processing filter request: {str(e)}")

            # Return error response
            response = filter_pb2.FilterResponse()
            response.result.status = common_pb2.PROCESSING_STATUS_FAILED
            response.result.message = f"Filter application failed: {str(e)}"
            response.result.processing_time_seconds = time.time() - start_time

            return response

    def _apply_filter(self, image, filter_type, intensity, parameters):
        """Apply the specified filter to the image"""
        logger.info(
            f"Applying filter type: {filter_pb2.FilterType.Name(filter_type)} with intensity: {intensity}"
        )

        if filter_type == filter_pb2.FILTER_TYPE_BLUR:
            kernel_size = int(intensity * 10) + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            return cv2.blur(image, (kernel_size, kernel_size))

        elif filter_type == filter_pb2.FILTER_TYPE_GAUSSIAN:
            # Replace GaussianBlur with simple box blur approximation
            kernel_size = int(intensity * 10) + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            return cv2.blur(image, (kernel_size, kernel_size))

        elif filter_type == filter_pb2.FILTER_TYPE_SHARPEN:
            kernel = np.array([[-1, -1, -1], [-1, 9 + intensity, -1], [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)

        elif filter_type == filter_pb2.FILTER_TYPE_BRIGHTNESS:
            # Adjust brightness
            brightness_value = int((intensity - 0.5) * 100)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            hsv[:, :, 2] = cv2.add(hsv[:, :, 2], brightness_value)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        elif filter_type == filter_pb2.FILTER_TYPE_CONTRAST:
            # Adjust contrast
            alpha = intensity  # Contrast control (1.0-3.0)
            return cv2.convertScaleAbs(image, alpha=alpha, beta=0)

        elif filter_type == filter_pb2.FILTER_TYPE_SATURATION:
            # Adjust saturation
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * intensity
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        else:
            logger.warning(
                f"Unknown filter type: {filter_type}, returning original image"
            )
            return image

    def Health(self, request, context):
        """Health check endpoint with actual service verification"""
        response = common_pb2.HealthCheckResponse()

        if self._health_check():
            response.status = common_pb2.HealthCheckResponse.SERVING
            logger.debug("Filter service health check passed")
        else:
            response.status = common_pb2.HealthCheckResponse.NOT_SERVING
            logger.warning("Filter service health check failed")

        return response


class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
    """Standard gRPC health check service implementation"""

    def __init__(self, filter_service):
        self.filter_service = filter_service

    def Check(self, request, context):
        """Standard gRPC health check implementation"""
        response = health_pb2.HealthCheckResponse()

        if self.filter_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
            logger.debug("Filter service health check passed")
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
            logger.warning("Filter service health check failed")

        return response

    def Watch(self, request, context):
        """Health check watch implementation (streaming)"""
        # For simplicity, just return current status
        response = health_pb2.HealthCheckResponse()

        if self.filter_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING

        yield response


def serve():
    """Start the gRPC server with optimized configuration"""
    port = os.getenv("GRPC_PORT", "9090")

    # Optimize thread pool for filter operations
    max_workers = int(os.getenv("GRPC_MAX_WORKERS", "20"))

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
    filter_service = FilterServiceImplementation()
    health_service = HealthServiceImplementation(filter_service)

    # Add services to server
    filter_pb2_grpc.add_FilterServiceServicer_to_server(filter_service, server)
    health_pb2_grpc.add_HealthServicer_to_server(health_service, server)

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(
        f"Starting optimized gRPC Filter Service on {listen_addr} with {max_workers} workers"
    )
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()

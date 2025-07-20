import sys
import os
import time
import logging
import asyncio
from concurrent import futures
from datetime import datetime, timezone

import grpc
from minio import Minio
import cv2
import numpy as np
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto paths
sys.path.append('/app/generated/python')
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')

from imageflow.v1 import resize_pb2
from imageflow.v1 import resize_pb2_grpc
from imageflow.v1 import common_pb2
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResizeServiceImplementation(resize_pb2_grpc.ResizeServiceServicer):
    """gRPC Resize service implementation with standard health checking"""
    def __init__(self):
        # MinIO client setup
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        # Create MinIO client pool for connection reuse
        self._create_minio_client()
        
        # Performance optimization: pre-warm OpenCV
        self._warm_up()
        
        logger.info(f"Initialized optimized MinIO client for {self.minio_endpoint}")

    def _create_minio_client(self):
        """Create MinIO client with optimized settings"""
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False
        )
        
    def _warm_up(self):
        """Pre-warm OpenCV and other libraries for better performance"""
        try:
            # Create a small dummy image to warm up OpenCV
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.resize(dummy, (50, 50))
            logger.info("Service warmed up successfully")
        except Exception as e:
            logger.warning(f"Warm-up failed: {e}")
            
    def _health_check(self):
        """Internal health check method"""
        try:
            # Test MinIO connection
            self.minio_client.list_buckets()
            # Test OpenCV functionality
            test_img = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.resize(test_img, (5, 5))
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def ResizeImage(self, request, context):
        """Handle single image resize request with performance optimization"""
        start_time = time.time()
        download_time = 0
        processing_time = 0
        upload_time = 0
        
        logger.info(f"Processing resize request for execution_id: {request.execution_id}")
        
        try:
            # Download image from MinIO with timing
            download_start = time.time()
            local_input = f"/tmp/input_{request.execution_id}_{int(time.time())}"
            local_output = f"/tmp/output_{request.execution_id}_{int(time.time())}"
            
            logger.info(f"Downloading {request.input_image.object_key} from bucket {request.input_image.bucket}")
            
            # Ensure bucket exists before attempting download
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                raise ValueError(f"Bucket {request.input_image.bucket} does not exist")
                
            self.minio_client.fget_object(
                request.input_image.bucket, 
                request.input_image.object_key, 
                local_input
            )
            download_time = time.time() - download_start
            logger.info(f"Download completed in {download_time:.2f}s")
            
            # Load and process image with timing
            processing_start = time.time()
            image = cv2.imread(local_input)
            if image is None:
                raise ValueError(f"Could not read input image: {request.input_image.object_key}")
            
            original_height, original_width = image.shape[:2]
            logger.info(f"Original image size: {original_width}x{original_height}")
            
            # Calculate target size with aspect ratio consideration
            if request.maintain_aspect_ratio:
                aspect_ratio = original_width / original_height
                if request.target_width / request.target_height > aspect_ratio:
                    new_width = int(request.target_height * aspect_ratio)
                    new_height = request.target_height
                else:
                    new_width = request.target_width
                    new_height = int(request.target_width / aspect_ratio)
            else:
                new_width = request.target_width
                new_height = request.target_height
            
            # Optimize resize interpolation based on scaling factor
            scale_factor = (new_width * new_height) / (original_width * original_height)
            if scale_factor < 0.5:
                interpolation = cv2.INTER_AREA  # Better for downscaling
            else:
                interpolation = cv2.INTER_LINEAR  # Faster for upscaling
                
            # Resize image
            resized_image = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
            logger.info(f"Resized image to {new_width}x{new_height}")
            
            # Save resized image with consistent naming
            input_file = request.input_image.object_key
            if input_file.endswith('.png'):
                output_path = input_file.replace('.png', '_resize.png')
            elif input_file.endswith(('.jpg', '.jpeg')):
                output_path = input_file.replace('.jpg', '_resize.jpg').replace('.jpeg', '_resize.jpg')
            else:
                # Default to jpg if no extension
                output_path = f"{input_file}_resize.jpg"
                
            # Optimize save parameters based on quality setting
            save_params = []
            if output_path.endswith(('.jpg', '.jpeg')):
                if request.quality == resize_pb2.RESIZE_QUALITY_HIGH:
                    save_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
                elif request.quality == resize_pb2.RESIZE_QUALITY_GOOD:
                    save_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
                else:  # RESIZE_QUALITY_FAST
                    save_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
            
            cv2.imwrite(local_output, resized_image, save_params)
            processing_time = time.time() - processing_start
            logger.info(f"Processing completed in {processing_time:.2f}s")
            
            # Upload to MinIO with timing
            upload_start = time.time()
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                self.minio_client.make_bucket(request.input_image.bucket)
                
            self.minio_client.fput_object(
                request.input_image.bucket,
                output_path,
                local_output
            )
            upload_time = time.time() - upload_start
            logger.info(f"Upload completed in {upload_time:.2f}s")
            
            # Cleanup local files
            try:
                if os.path.exists(local_input):
                    os.remove(local_input)
                if os.path.exists(local_output):
                    os.remove(local_output)
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
            
            total_time = time.time() - start_time
            
            # Create response with detailed timing
            response = resize_pb2.ResizeResponse()
            
            # Set processing result
            response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
            response.result.message = f"Image resize completed successfully (total: {total_time:.2f}s, download: {download_time:.2f}s, processing: {processing_time:.2f}s, upload: {upload_time:.2f}s)"
            
            # Set output image info
            response.result.output_image.bucket = request.input_image.bucket
            response.result.output_image.object_key = output_path
            response.result.output_image.content_type = "image/jpeg" if output_path.endswith('.jpg') else "image/png"
            response.result.output_image.width = new_width
            response.result.output_image.height = new_height
            
            # Set timestamp
            now = Timestamp()
            now.FromDatetime(datetime.now(timezone.utc))
            response.result.processed_at.CopyFrom(now)
            response.result.processing_time_seconds = total_time
            
            # Set metadata with detailed timing
            response.metadata.original_width = original_width
            response.metadata.original_height = original_height
            response.metadata.output_width = new_width
            response.metadata.output_height = new_height
            response.metadata.scale_factor_x = new_width / original_width
            response.metadata.scale_factor_y = new_height / original_height
            response.metadata.quality_used = request.quality
            
            logger.info(f"Resize completed successfully - Total: {total_time:.2f}s (download: {download_time:.2f}s, processing: {processing_time:.2f}s, upload: {upload_time:.2f}s)")
            return response
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error processing resize request (after {total_time:.2f}s): {str(e)}")
            
            # Cleanup on error
            try:
                if 'local_input' in locals() and os.path.exists(local_input):
                    os.remove(local_input)
                if 'local_output' in locals() and os.path.exists(local_output):
                    os.remove(local_output)
            except Exception:
                pass
            
            # Return error response
            response = resize_pb2.ResizeResponse()
            response.result.status = common_pb2.PROCESSING_STATUS_FAILED
            response.result.message = f"Resize failed: {str(e)}"
            response.result.processing_time_seconds = total_time
            
            return response


class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
    """Standard gRPC health check service implementation"""
    
    def __init__(self, resize_service):
        self.resize_service = resize_service
    
    def Check(self, request, context):
        """Standard gRPC health check implementation"""
        response = health_pb2.HealthCheckResponse()
        
        if self.resize_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
            logger.debug("Health check passed")
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
            logger.warning("Health check failed")
            
        return response
    
    def Watch(self, request, context):
        """Health check watch implementation (streaming)"""
        # For simplicity, just return current status
        response = health_pb2.HealthCheckResponse()
        
        if self.resize_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
            
        yield response


def serve():
    """Start the gRPC server with optimized configuration"""
    port = os.getenv("GRPC_PORT", "9090")
    
    # Optimize thread pool for better concurrency
    max_workers = int(os.getenv("GRPC_MAX_WORKERS", "20"))
    
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
    resize_service = ResizeServiceImplementation()
    health_service = HealthServiceImplementation(resize_service)
    
    # Add services to server
    resize_pb2_grpc.add_ResizeServiceServicer_to_server(resize_service, server)
    health_pb2_grpc.add_HealthServicer_to_server(health_service, server)
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting optimized gRPC Resize Service on {listen_addr} with {max_workers} workers")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)

if __name__ == '__main__':
    serve()
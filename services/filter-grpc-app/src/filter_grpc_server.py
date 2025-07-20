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
from google.protobuf.timestamp_pb2 import Timestamp

# Add generated proto path
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')

from imageflow.v1 import filter_pb2
from imageflow.v1 import filter_pb2_grpc
from imageflow.v1 import common_pb2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FilterServiceImplementation(filter_pb2_grpc.FilterServiceServicer):
    def __init__(self):
        # MinIO client setup
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False
        )
        logger.info(f"Initialized MinIO client for {self.minio_endpoint}")

    def ApplyFilter(self, request, context):
        """Handle filter application request"""
        start_time = time.time()
        logger.info(f"Processing filter request for execution_id: {request.execution_id}")
        
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
            
            # Apply filter
            filtered_image = self._apply_filter(
                image, 
                request.filter_type,
                request.intensity,
                request.parameters
            )
            
            # Save filtered image
            output_path = request.input_image.object_key.replace('.png', '_filtered.png').replace('.jpg', '_filtered.jpg')
            if not output_path.endswith(('.png', '.jpg', '.jpeg')):
                output_path += '.jpg'
                
            cv2.imwrite(local_output, filtered_image)
            
            # Upload to MinIO
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                self.minio_client.make_bucket(request.input_image.bucket)
                
            self.minio_client.fput_object(
                request.input_image.bucket,
                output_path,
                local_output
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
            response.result.output_image.content_type = "image/jpeg" if output_path.endswith('.jpg') else "image/png"
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
        logger.info(f"Applying filter type: {filter_pb2.FilterType.Name(filter_type)} with intensity: {intensity}")
        
        if filter_type == filter_pb2.FILTER_TYPE_BLUR:
            kernel_size = int(intensity * 10) + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            return cv2.blur(image, (kernel_size, kernel_size))
            
        elif filter_type == filter_pb2.FILTER_TYPE_GAUSSIAN:
            kernel_size = int(intensity * 10) + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            sigma = intensity * 2
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
            
        elif filter_type == filter_pb2.FILTER_TYPE_SHARPEN:
            kernel = np.array([[-1, -1, -1],
                             [-1, 9 + intensity, -1],
                             [-1, -1, -1]])
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
            logger.warning(f"Unknown filter type: {filter_type}, returning original image")
            return image

    def Health(self, request, context):
        """Health check endpoint"""
        response = common_pb2.HealthCheckResponse()
        response.status = common_pb2.HealthCheckResponse.SERVING
        return response

def serve():
    """Start the gRPC server"""
    port = os.getenv("GRPC_PORT", "9090")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    filter_pb2_grpc.add_FilterServiceServicer_to_server(
        FilterServiceImplementation(), server
    )
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting gRPC Filter Service on {listen_addr}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)

if __name__ == '__main__':
    serve()
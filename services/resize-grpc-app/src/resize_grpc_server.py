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

# Add generated proto path
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')

from imageflow.v1 import resize_pb2
from imageflow.v1 import resize_pb2_grpc
from imageflow.v1 import common_pb2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResizeServiceImplementation(resize_pb2_grpc.ResizeServiceServicer):
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

    def ResizeImage(self, request, context):
        """Handle single image resize request"""
        start_time = time.time()
        logger.info(f"Processing resize request for execution_id: {request.execution_id}")
        
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
            
            # Load and process image
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
            
            # Resize image
            resized_image = cv2.resize(image, (new_width, new_height))
            logger.info(f"Resized image to {new_width}x{new_height}")
            
            # Save resized image
            output_path = request.input_image.object_key.replace('.png', '_resized.png').replace('.jpg', '_resized.jpg')
            if not output_path.endswith(('.png', '.jpg', '.jpeg')):
                output_path += '.jpg'
                
            cv2.imwrite(local_output, resized_image)
            
            # Upload to MinIO
            if not self.minio_client.bucket_exists(request.input_image.bucket):
                self.minio_client.make_bucket(request.input_image.bucket)
                
            self.minio_client.fput_object(
                request.input_image.bucket,
                output_path,
                local_output
            )
            logger.info(f"Uploaded resized image to {output_path}")
            
            # Cleanup local files
            if os.path.exists(local_input):
                os.remove(local_input)
            if os.path.exists(local_output):
                os.remove(local_output)
            
            processing_time = time.time() - start_time
            
            # Create response
            response = resize_pb2.ResizeResponse()
            
            # Set processing result
            response.result.status = common_pb2.PROCESSING_STATUS_COMPLETED
            response.result.message = "Image resize completed successfully"
            
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
            response.result.processing_time_seconds = processing_time
            
            # Set metadata
            response.metadata.original_width = original_width
            response.metadata.original_height = original_height
            response.metadata.output_width = new_width
            response.metadata.output_height = new_height
            response.metadata.scale_factor_x = new_width / original_width
            response.metadata.scale_factor_y = new_height / original_height
            response.metadata.quality_used = request.quality
            
            logger.info(f"Resize completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Error processing resize request: {str(e)}")
            
            # Return error response
            response = resize_pb2.ResizeResponse()
            response.result.status = common_pb2.PROCESSING_STATUS_FAILED
            response.result.message = f"Resize failed: {str(e)}"
            response.result.processing_time_seconds = time.time() - start_time
            
            return response

    def Health(self, request, context):
        """Health check endpoint"""
        response = common_pb2.HealthCheckResponse()
        response.status = common_pb2.HealthCheckResponse.SERVING
        return response

def serve():
    """Start the gRPC server"""
    port = os.getenv("GRPC_PORT", "9090")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    resize_pb2_grpc.add_ResizeServiceServicer_to_server(
        ResizeServiceImplementation(), server
    )
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting gRPC Resize Service on {listen_addr}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)

if __name__ == '__main__':
    serve()
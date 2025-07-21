import sys
import os
import time
import logging
import asyncio
from concurrent import futures
from datetime import datetime, timezone
import threading
import queue

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
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CameraStreamProcessorImplementation(
    camera_stream_pb2_grpc.CameraStreamProcessorServicer
):
    def __init__(self):
        # AI detection service endpoint
        self.ai_detection_endpoint = os.getenv("AI_DETECTION_GRPC_ENDPOINT", "ai-detection-grpc-service:9090")
        
        # Frame processing parameters
        self.max_concurrent_streams = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
        self.frame_skip_threshold = int(os.getenv("FRAME_SKIP_THRESHOLD", "100"))  # ms
        
        logger.info(f"CameraStreamProcessor initialized with AI Detection: {self.ai_detection_endpoint}")
        logger.info(f"Max concurrent streams: {self.max_concurrent_streams}")

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
                    logger.debug(f"Frame processed in {processing_time:.2f}ms for source {video_frame.metadata.source_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing frame from {video_frame.metadata.source_id}: {e}")
                    
                    # Send error response
                    error_frame = camera_stream_pb2.ProcessedFrame()
                    error_frame.source_id = video_frame.metadata.source_id
                    error_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_FAILED
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
        Process a single video frame through the pipeline
        """
        start_time = time.time()
        
        # Create response frame
        processed_frame = camera_stream_pb2.ProcessedFrame()
        processed_frame.source_id = video_frame.metadata.source_id
        
        try:
            # Check if we should skip this frame for performance
            if self._should_skip_frame(video_frame):
                processed_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_SKIPPED
                processed_frame.error_message = "Frame skipped due to high load"
                return processed_frame
            
            # Determine processing pipeline based on metadata
            pipeline_id = video_frame.metadata.pipeline_id
            
            if pipeline_id == "ai_detection":
                # Process with AI detection
                detections = self._process_ai_detection(video_frame)
                processed_frame.detections.extend(detections)
                processed_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
                
            elif pipeline_id == "passthrough":
                # Simple passthrough for testing
                processed_frame.processed_data = video_frame.frame_data
                processed_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
                
            else:
                # Default: basic frame validation
                self._validate_frame(video_frame.frame_data)
                processed_frame.status = camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS
            
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

    def _should_skip_frame(self, video_frame):
        """
        Determine if frame should be skipped based on load
        """
        # Simple heuristic: check frame age
        current_time = int(time.time() * 1000)
        frame_age = current_time - video_frame.timestamp_ms
        
        if frame_age > self.frame_skip_threshold:
            logger.debug(f"Skipping old frame (age: {frame_age}ms)")
            return True
        
        return False

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

    def _process_ai_detection(self, video_frame):
        """
        Process frame with AI detection service
        For real-time processing, we can't use file storage, so we need to modify approach
        """
        try:
            # For now, simulate AI detection results
            # In real implementation, this would call the AI detection service with frame data
            
            # Decode frame to get dimensions
            image = Image.open(io.BytesIO(video_frame.frame_data))
            width, height = image.size
            
            # Create mock detection (in real implementation, call AI service)
            detection = camera_stream_pb2.Detection()
            detection.class_name = "person"
            detection.confidence = 0.85
            
            # Create bounding box (reuse existing BoundingBox from ai_detection.proto)
            bbox = ai_detection_pb2.BoundingBox()
            bbox.x1 = 100
            bbox.y1 = 100
            bbox.x2 = 200
            bbox.y2 = 250
            detection.bbox.CopyFrom(bbox)
            
            return [detection]
            
        except Exception as e:
            logger.error(f"AI detection error: {e}")
            return []


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
    health_pb2_grpc.add_HealthServicer_to_server(
        HealthServiceImplementation(), server
    )
    
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
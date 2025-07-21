from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
import base64
import io
from PIL import Image
import cv2
import numpy as np
from typing import Dict, List
import sys
import os

# Add generated proto path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../generated/python'))

import grpc
from imageflow.v1 import camera_stream_pb2
from imageflow.v1 import camera_stream_pb2_grpc

logger = logging.getLogger(__name__)

router = APIRouter()

# Connected clients for real-time streaming
connected_clients: Dict[str, WebSocket] = {}


class CameraStreamManager:
    def __init__(self):
        self.camera_stream_endpoint = os.getenv("CAMERA_STREAM_GRPC_ENDPOINT", "camera-stream-grpc-service:9090")
        self.active_streams: Dict[str, asyncio.Task] = {}
        
    def get_camera_stream_client(self):
        """Get gRPC client for camera stream service"""
        channel = grpc.insecure_channel(self.camera_stream_endpoint)
        return camera_stream_pb2_grpc.CameraStreamProcessorStub(channel)


stream_manager = CameraStreamManager()


@router.websocket("/ws/camera-stream/{source_id}")
async def camera_stream_websocket(websocket: WebSocket, source_id: str):
    """
    WebSocket endpoint for real-time camera streaming
    Receives video frames via WebSocket and processes them through gRPC streaming
    """
    await websocket.accept()
    connected_clients[source_id] = websocket
    
    logger.info(f"Camera stream WebSocket connected for source: {source_id}")
    
    try:
        # Start gRPC streaming task
        stream_task = asyncio.create_task(
            handle_grpc_streaming(websocket, source_id)
        )
        stream_manager.active_streams[source_id] = stream_task
        
        # Keep connection alive and handle incoming frames
        async for data in websocket.iter_text():
            try:
                message = json.loads(data)
                
                if message.get("type") == "frame":
                    # Process incoming frame
                    await process_incoming_frame(message, source_id)
                elif message.get("type") == "config":
                    # Handle configuration updates
                    await handle_config_update(message, source_id)
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {source_id}")
            except Exception as e:
                logger.error(f"Error processing message from {source_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"Camera stream WebSocket disconnected for source: {source_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {source_id}: {e}")
    finally:
        # Cleanup
        if source_id in connected_clients:
            del connected_clients[source_id]
        if source_id in stream_manager.active_streams:
            stream_manager.active_streams[source_id].cancel()
            del stream_manager.active_streams[source_id]


async def handle_grpc_streaming(websocket: WebSocket, source_id: str):
    """
    Handle bidirectional gRPC streaming with camera stream service
    """
    try:
        client = stream_manager.get_camera_stream_client()
        
        # Create a queue for frames to be sent to gRPC service
        frame_queue = asyncio.Queue()
        
        # Store frame queue for this source
        setattr(websocket, 'frame_queue', frame_queue)
        
        async def frame_generator():
            """Generator for frames to send to gRPC service"""
            while True:
                try:
                    frame = await frame_queue.get()
                    if frame is None:  # Sentinel to stop
                        break
                    yield frame
                except asyncio.CancelledError:
                    break
        
        # Start gRPC streaming
        async def process_grpc_stream():
            try:
                response_stream = client.ProcessVideoStream(frame_generator())
                
                # Process responses from gRPC service
                async for processed_frame in response_stream:
                    try:
                        # Send processed frame back to client via WebSocket
                        response_data = {
                            "type": "processed_frame",
                            "source_id": processed_frame.source_id,
                            "status": processed_frame.status,
                            "processing_time_ms": processed_frame.processing_time_ms,
                            "detections": [
                                {
                                    "class_name": detection.class_name,
                                    "confidence": detection.confidence,
                                    "bbox": {
                                        "x1": detection.bbox.x1,
                                        "y1": detection.bbox.y1,
                                        "x2": detection.bbox.x2,
                                        "y2": detection.bbox.y2,
                                    }
                                }
                                for detection in processed_frame.detections
                            ]
                        }
                        
                        if processed_frame.error_message:
                            response_data["error"] = processed_frame.error_message
                        
                        await websocket.send_text(json.dumps(response_data))
                        
                    except Exception as e:
                        logger.error(f"Error sending processed frame to {source_id}: {e}")
                        break
            except Exception as e:
                logger.error(f"gRPC streaming error for {source_id}: {e}")
        
        # Run the gRPC stream processing
        await process_grpc_stream()
                
    except grpc.RpcError as e:
        logger.error(f"gRPC streaming error for {source_id}: {e}")
    except Exception as e:
        logger.error(f"Streaming handler error for {source_id}: {e}")


async def process_incoming_frame(message: dict, source_id: str):
    """
    Process incoming frame from WebSocket client
    """
    try:
        # Extract frame data
        frame_data_b64 = message.get("frame_data")
        if not frame_data_b64:
            logger.error(f"No frame data in message from {source_id}")
            return
        
        # Decode base64 frame data
        frame_data = base64.b64decode(frame_data_b64)
        
        # Create VideoFrame message
        video_frame = camera_stream_pb2.VideoFrame()
        video_frame.frame_data = frame_data
        video_frame.timestamp_ms = message.get("timestamp_ms", 0)
        
        # Set metadata
        metadata = video_frame.metadata
        metadata.source_id = source_id
        metadata.width = message.get("width", 0)
        metadata.height = message.get("height", 0)
        metadata.pipeline_id = message.get("pipeline_id", "ai_detection")
        
        # Add processing parameters
        processing_params = message.get("processing_params", {})
        for key, value in processing_params.items():
            metadata.processing_params[key] = str(value)
        
        # Send frame to gRPC service via queue
        websocket = connected_clients.get(source_id)
        if websocket and hasattr(websocket, 'frame_queue'):
            await websocket.frame_queue.put(video_frame)
        
    except Exception as e:
        logger.error(f"Error processing incoming frame from {source_id}: {e}")


async def handle_config_update(message: dict, source_id: str):
    """
    Handle configuration updates from client
    """
    try:
        config = message.get("config", {})
        logger.info(f"Config update for {source_id}: {config}")
        
        # Send acknowledgment
        websocket = connected_clients.get(source_id)
        if websocket:
            response = {
                "type": "config_ack",
                "source_id": source_id,
                "status": "updated"
            }
            await websocket.send_text(json.dumps(response))
            
    except Exception as e:
        logger.error(f"Error handling config update for {source_id}: {e}")


@router.post("/v1/camera-stream/test-frame")
async def test_frame_processing(
    file: UploadFile = File(...),
    pipeline_id: str = "ai_detection",
    source_id: str = "test_camera"
):
    """
    Test endpoint for single frame processing via camera stream service
    """
    try:
        # Read uploaded image
        image_data = await file.read()
        
        # Validate image
        try:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")
        
        # Create gRPC client
        client = stream_manager.get_camera_stream_client()
        
        # Create VideoFrame
        video_frame = camera_stream_pb2.VideoFrame()
        video_frame.frame_data = image_data
        video_frame.timestamp_ms = int(asyncio.get_event_loop().time() * 1000)
        
        metadata = video_frame.metadata
        metadata.source_id = source_id
        metadata.width = width
        metadata.height = height
        metadata.pipeline_id = pipeline_id
        
        # Process single frame (simulate streaming with single frame)
        async def single_frame_generator():
            yield video_frame
        
        # Get response using asyncio to handle the streaming properly
        try:
            response_stream = client.ProcessVideoStream(single_frame_generator())
            
            # Get first (and only) response
            async for processed_frame in response_stream:
                result = {
                    "source_id": processed_frame.source_id,
                    "status": processed_frame.status,
                    "processing_time_ms": processed_frame.processing_time_ms,
                    "detections": [
                        {
                            "class_name": detection.class_name,
                            "confidence": detection.confidence,
                            "bbox": {
                                "x1": detection.bbox.x1,
                                "y1": detection.bbox.y1,
                                "x2": detection.bbox.x2,
                                "y2": detection.bbox.y2,
                            }
                        }
                        for detection in processed_frame.detections
                    ]
                }
                
                if processed_frame.error_message:
                    result["error"] = processed_frame.error_message
                
                return result
        except Exception as e:
            logger.error(f"Error in gRPC stream: {e}")
            raise HTTPException(status_code=500, detail=f"gRPC streaming error: {e}")
        
        # If no response received
        raise HTTPException(status_code=500, detail="No response from camera stream service")
        
    except grpc.RpcError as e:
        logger.error(f"gRPC error in test frame processing: {e}")
        raise HTTPException(status_code=500, detail=f"gRPC service error: {e.details()}")
    except Exception as e:
        logger.error(f"Error in test frame processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/camera-stream/status")
async def get_streaming_status():
    """
    Get status of active camera streams
    """
    return {
        "active_streams": list(stream_manager.active_streams.keys()),
        "connected_clients": list(connected_clients.keys()),
        "total_active": len(stream_manager.active_streams)
    }
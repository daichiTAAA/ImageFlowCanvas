from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    UploadFile,
    File,
    Depends,
)
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
import base64
import io
import time
from PIL import Image
import cv2
import numpy as np
from typing import Dict, List
import sys
import os
import concurrent.futures

# Add generated proto path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../generated/python"))

import grpc
from imageflow.v1 import camera_stream_pb2
from imageflow.v1 import camera_stream_pb2_grpc

# Import pipeline service and dependencies
from app.services.pipeline_service import PipelineService
from app.services.auth_service import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()

# Connected clients for real-time streaming
connected_clients: Dict[str, WebSocket] = {}

# Pipeline service instance
pipeline_service = PipelineService()


@router.get("/camera-stream/pipelines")
async def get_available_pipelines(
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Get list of available pipelines for real-time camera stream processing
    """
    try:
        pipelines = await pipeline_service.get_all_pipelines(db)

        # Format pipelines for camera stream usage
        camera_pipelines = []
        for pipeline in pipelines:
            # Check if pipeline is suitable for real-time processing
            # (contains supported component types)
            supported_components = {"resize", "ai_detection", "filter"}
            has_supported_components = any(
                comp.component_type in supported_components
                for comp in pipeline.components
            )

            if has_supported_components:
                camera_pipelines.append(
                    {
                        "id": pipeline.id,
                        "name": pipeline.name,
                        "description": pipeline.description,
                        "components": [
                            {
                                "name": comp.name,
                                "type": comp.component_type,
                                "parameters": comp.parameters,
                            }
                            for comp in pipeline.components
                            if comp.component_type in supported_components
                        ],
                    }
                )

        return {
            "pipelines": camera_pipelines,
            "supported_components": list(supported_components),
            "message": f"Found {len(camera_pipelines)} pipelines suitable for real-time processing",
        }

    except Exception as e:
        logger.error(f"Error fetching pipelines for camera stream: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipelines: {e}")


class CameraStreamManager:
    def __init__(self):
        self.camera_stream_endpoint = os.getenv(
            "CAMERA_STREAM_GRPC_ENDPOINT",
            "camera-stream-grpc-service.image-processing.svc.cluster.local:9090",
        )
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
    logger.info(f"=== NEW WEBSOCKET CONNECTION ATTEMPT ===")
    logger.info(f"Source ID: {source_id}")
    logger.info(f"WebSocket client: {websocket.client}")

    await websocket.accept()
    connected_clients[source_id] = websocket

    logger.info(f"Camera stream WebSocket connected for source: {source_id}")
    logger.info(f"Total connected clients: {len(connected_clients)}")

    try:
        # Start gRPC streaming task
        stream_task = asyncio.create_task(handle_grpc_streaming(websocket, source_id))
        stream_manager.active_streams[source_id] = stream_task

        # Keep connection alive and handle incoming frames
        async for data in websocket.iter_text():
            try:
                logger.info(
                    f"Received WebSocket data from {source_id}: {len(data)} chars"
                )

                # Debug: Log first 200 chars of data to see what we're receiving
                logger.debug(
                    f"WebSocket data preview from {source_id}: {data[:200]}..."
                )

                message = json.loads(data)
                logger.info(
                    f"Parsed message type: {message.get('type', 'unknown')} from {source_id}"
                )

                # Debug: Log message keys to understand structure
                logger.debug(f"Message keys from {source_id}: {list(message.keys())}")

                if message.get("type") == "frame":
                    # Process incoming frame
                    await process_incoming_frame(message, source_id)
                elif message.get("type") == "config":
                    # Handle configuration updates
                    await handle_config_update(message, source_id)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from {source_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing message from {source_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"Camera stream WebSocket disconnected for source: {source_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {source_id}: {e}")
    finally:
        # Cleanup
        logger.info(f"Cleaning up resources for {source_id}")

        if source_id in connected_clients:
            del connected_clients[source_id]
            logger.info(f"Removed {source_id} from connected clients")

        if source_id in stream_manager.active_streams:
            try:
                stream_manager.active_streams[source_id].cancel()
                logger.info(f"Cancelled stream task for {source_id}")
            except Exception as e:
                logger.error(f"Error cancelling stream task for {source_id}: {e}")
            finally:
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
        setattr(websocket, "frame_queue", frame_queue)

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
                logger.info(f"Starting gRPC stream processing for {source_id}")

                # Simpler approach: process frames one by one
                while True:
                    try:
                        # Wait for frame from queue
                        frame = await asyncio.wait_for(frame_queue.get(), timeout=30.0)
                        if frame is None:  # Sentinel to stop
                            break

                        logger.info(f"Processing frame for {source_id}")
                        logger.debug(
                            f"Frame metadata: source_id={frame.metadata.source_id}, size={len(frame.frame_data)}, dimensions={frame.metadata.width}x{frame.metadata.height}"
                        )

                        # Process single frame in executor
                        loop = asyncio.get_event_loop()

                        def process_single_frame():
                            try:
                                # Create a simple generator for single frame
                                def single_frame_gen():
                                    yield frame

                                logger.info(
                                    f"Calling gRPC ProcessVideoStream for {source_id}"
                                )

                                # Call gRPC service
                                response_stream = client.ProcessVideoStream(
                                    single_frame_gen()
                                )

                                # Get first response
                                for processed_frame in response_stream:
                                    logger.info(
                                        f"Received processed frame from gRPC for {source_id}"
                                    )
                                    return processed_frame

                                logger.warning(
                                    f"No response from gRPC service for {source_id}"
                                )
                                return None
                            except Exception as e:
                                logger.error(
                                    f"gRPC processing error for {source_id}: {e}"
                                )
                                import traceback

                                logger.error(
                                    f"gRPC traceback: {traceback.format_exc()}"
                                )
                                return None

                        # Run in executor
                        processed_frame = await loop.run_in_executor(
                            None, process_single_frame
                        )

                        if processed_frame:
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
                                        },
                                    }
                                    for detection in processed_frame.detections
                                ],
                            }

                            if processed_frame.error_message:
                                response_data["error"] = processed_frame.error_message

                            await websocket.send_text(json.dumps(response_data))
                            logger.info(f"Sent processed frame result to {source_id}")
                        else:
                            logger.warning(
                                f"No processed frame received for {source_id}"
                            )

                    except asyncio.TimeoutError:
                        # Timeout waiting for frame - continue loop
                        continue
                    except Exception as e:
                        logger.error(f"Error in frame processing loop: {e}")
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
        logger.info(
            f"Received frame from {source_id}: {message.get('type', 'unknown')}"
        )

        # Debug: Log all message keys
        logger.debug(f"Frame message keys: {list(message.keys())}")
        logger.debug(
            f"Frame message values (except frame_data): {dict((k, v) for k, v in message.items() if k != 'frame_data')}"
        )

        # Extract frame data
        frame_data_b64 = message.get("frame_data")
        if not frame_data_b64:
            logger.error(f"No frame data in message from {source_id}")
            logger.error(f"Available keys: {list(message.keys())}")
            return

        # Decode base64 frame data
        try:
            frame_data = base64.b64decode(frame_data_b64)
            logger.info(f"Decoded frame data size: {len(frame_data)} bytes")
        except Exception as e:
            logger.error(f"Failed to decode base64 frame data from {source_id}: {e}")
            logger.error(f"Frame data preview: {frame_data_b64[:100]}...")
            return

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

        logger.info(
            f"Frame metadata: {metadata.width}x{metadata.height}, pipeline: {metadata.pipeline_id}"
        )

        # Add processing parameters
        processing_params = message.get("processing_params", {})
        for key, value in processing_params.items():
            metadata.processing_params[key] = str(value)

        # Send frame to gRPC service via queue
        websocket = connected_clients.get(source_id)
        if websocket and hasattr(websocket, "frame_queue"):
            await websocket.frame_queue.put(video_frame)
            logger.info(f"Frame queued for processing by {source_id}")
            logger.debug(
                f"Queue size after adding frame: {websocket.frame_queue.qsize()}"
            )
        else:
            logger.error(f"No frame queue found for {source_id}")
            logger.error(f"Websocket exists: {websocket is not None}")
            logger.error(
                f"Has frame_queue attr: {hasattr(websocket, 'frame_queue') if websocket else 'N/A'}"
            )

    except Exception as e:
        logger.error(f"Error processing incoming frame from {source_id}: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")


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
                "status": "updated",
            }
            await websocket.send_text(json.dumps(response))

    except Exception as e:
        logger.error(f"Error handling config update for {source_id}: {e}")


@router.post("/camera-stream/test-frame")
async def test_frame_processing(
    file: UploadFile = File(...),
    pipeline_id: str = "ai_detection",
    source_id: str = "test_camera",
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
        video_frame.timestamp_ms = int(time.time() * 1000)  # UNIX時間を使用

        metadata = video_frame.metadata
        metadata.source_id = source_id
        metadata.width = width
        metadata.height = height
        metadata.pipeline_id = pipeline_id

        # Process single frame (simulate streaming with single frame)
        def single_frame_generator():
            yield video_frame

        # Get response using run_in_executor to handle the gRPC call
        try:
            loop = asyncio.get_event_loop()

            def call_grpc_stream():
                response_stream = client.ProcessVideoStream(single_frame_generator())
                # Get first (and only) response
                for processed_frame in response_stream:
                    return processed_frame
                return None

            processed_frame = await loop.run_in_executor(None, call_grpc_stream)

            if processed_frame:
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
                            },
                        }
                        for detection in processed_frame.detections
                    ],
                }

                if processed_frame.error_message:
                    result["error"] = processed_frame.error_message

                return result
            else:
                raise HTTPException(
                    status_code=500, detail="No response from camera stream service"
                )
        except Exception as e:
            logger.error(f"Error in gRPC stream: {e}")
            raise HTTPException(status_code=500, detail=f"gRPC streaming error: {e}")

    except grpc.RpcError as e:
        logger.error(f"gRPC error in test frame processing: {e}")
        raise HTTPException(
            status_code=500, detail=f"gRPC service error: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in test frame processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/camera-stream/status")
async def get_streaming_status():
    """
    Get status of active camera streams
    """
    return {
        "active_streams": list(stream_manager.active_streams.keys()),
        "connected_clients": list(connected_clients.keys()),
        "total_active": len(stream_manager.active_streams),
    }

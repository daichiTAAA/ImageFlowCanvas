#!/usr/bin/env python3
"""
Test client for real-time camera streaming
This client simulates a camera feed by sending test images to the streaming service
"""

import asyncio
import websockets
import json
import base64
import time
import cv2
import numpy as np
from PIL import Image
import io
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_frame(width=640, height=480, frame_number=0):
    """
    Create a test frame with a simple pattern
    """
    # Create a test image with gradient and frame number
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add gradient
    for y in range(height):
        for x in range(width):
            image[y, x] = [
                int(255 * x / width),
                int(255 * y / height),
                int(255 * (frame_number % 100) / 100)
            ]
    
    # Add frame number text
    cv2.putText(image, f"Frame {frame_number}", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Convert to JPEG bytes
    _, buffer = cv2.imencode('.jpg', image)
    return buffer.tobytes()


async def test_websocket_streaming(uri, source_id="test_camera", num_frames=50, fps=10):
    """
    Test WebSocket streaming with the camera stream service
    """
    logger.info(f"Connecting to {uri} for source {source_id}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("WebSocket connected, starting streaming...")
            
            # Send configuration
            config_message = {
                "type": "config",
                "config": {
                    "pipeline_id": "ai_detection",
                    "processing_params": {
                        "model_name": "yolo",
                        "confidence_threshold": "0.5"
                    }
                }
            }
            await websocket.send(json.dumps(config_message))
            
            # Start frame sending task
            send_task = asyncio.create_task(
                send_frames(websocket, source_id, num_frames, fps)
            )
            
            # Start response handling task
            receive_task = asyncio.create_task(
                receive_responses(websocket, source_id)
            )
            
            # Wait for tasks to complete
            await asyncio.gather(send_task, receive_task)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def send_frames(websocket, source_id, num_frames, fps):
    """
    Send test frames to the WebSocket
    """
    frame_interval = 1.0 / fps
    
    for frame_num in range(num_frames):
        try:
            # Create test frame
            frame_data = create_test_frame(frame_number=frame_num)
            frame_data_b64 = base64.b64encode(frame_data).decode('utf-8')
            
            # Create frame message
            frame_message = {
                "type": "frame",
                "frame_data": frame_data_b64,
                "timestamp_ms": int(time.time() * 1000),
                "width": 640,
                "height": 480,
                "pipeline_id": "ai_detection",
                "processing_params": {
                    "model_name": "yolo",
                    "confidence_threshold": "0.5"
                }
            }
            
            # Send frame
            await websocket.send(json.dumps(frame_message))
            logger.info(f"Sent frame {frame_num + 1}/{num_frames}")
            
            # Wait for next frame time
            await asyncio.sleep(frame_interval)
            
        except Exception as e:
            logger.error(f"Error sending frame {frame_num}: {e}")
            break
    
    logger.info("Finished sending frames")


async def receive_responses(websocket, source_id):
    """
    Receive and process responses from the WebSocket
    """
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "processed_frame":
                    logger.info(f"Received processed frame for {data.get('source_id')}")
                    logger.info(f"  Status: {data.get('status')}")
                    logger.info(f"  Processing time: {data.get('processing_time_ms')}ms")
                    
                    detections = data.get("detections", [])
                    if detections:
                        logger.info(f"  Detections: {len(detections)}")
                        for detection in detections:
                            logger.info(f"    - {detection['class_name']}: {detection['confidence']:.2f}")
                    
                    if data.get("error"):
                        logger.error(f"  Error: {data['error']}")
                
                elif message_type == "config_ack":
                    logger.info(f"Configuration acknowledged for {data.get('source_id')}")
                
                else:
                    logger.info(f"Received message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error("Received invalid JSON")
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"Error receiving responses: {e}")


async def test_http_endpoint(base_url, image_path=None):
    """
    Test the HTTP endpoint for single frame processing
    """
    import aiohttp
    import aiofiles
    
    url = f"{base_url}/v1/camera-stream/test-frame"
    
    # Create or load test image
    if image_path:
        async with aiofiles.open(image_path, 'rb') as f:
            image_data = await f.read()
    else:
        # Create test image
        test_frame = create_test_frame()
        image_data = test_frame
    
    # Send request
    data = aiohttp.FormData()
    data.add_field('file', image_data, filename='test.jpg', content_type='image/jpeg')
    data.add_field('pipeline_id', 'ai_detection')
    data.add_field('source_id', 'test_http')
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("HTTP test successful:")
                    logger.info(f"  Status: {result.get('status')}")
                    logger.info(f"  Processing time: {result.get('processing_time_ms')}ms")
                    
                    detections = result.get('detections', [])
                    if detections:
                        logger.info(f"  Detections: {len(detections)}")
                        for detection in detections:
                            logger.info(f"    - {detection['class_name']}: {detection['confidence']:.2f}")
                else:
                    logger.error(f"HTTP request failed: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error: {error_text}")
                    
        except Exception as e:
            logger.error(f"HTTP test error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Test real-time camera streaming")
    parser.add_argument("--host", default="localhost", help="Backend host")
    parser.add_argument("--port", default="8000", help="Backend port")
    parser.add_argument("--source-id", default="test_camera", help="Camera source ID")
    parser.add_argument("--frames", type=int, default=20, help="Number of frames to send")
    parser.add_argument("--fps", type=int, default=5, help="Frames per second")
    parser.add_argument("--test-http", action="store_true", help="Test HTTP endpoint only")
    parser.add_argument("--image", help="Path to test image file")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    ws_url = f"ws://{args.host}:{args.port}/v1/ws/camera-stream/{args.source_id}"
    
    if args.test_http:
        logger.info("Testing HTTP endpoint...")
        await test_http_endpoint(base_url, args.image)
    else:
        logger.info("Testing WebSocket streaming...")
        await test_websocket_streaming(ws_url, args.source_id, args.frames, args.fps)


if __name__ == "__main__":
    asyncio.run(main())
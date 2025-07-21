#!/usr/bin/env python3
"""
Comprehensive validation script for camera stream integration with Web UI pipelines
"""

import asyncio
import json
import base64
import requests
import websockets
from PIL import Image
import io
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraStreamValidator:
    def __init__(self, backend_url="http://localhost:8000", websocket_url="ws://localhost:8000"):
        self.backend_url = backend_url
        self.websocket_url = websocket_url
        self.auth_token = None

    async def authenticate(self):
        """Authenticate with the backend to get access token"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=10
            )
            if response.status_code == 200:
                self.auth_token = response.json()["access_token"]
                logger.info("✅ Authentication successful")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    async def get_available_pipelines(self):
        """Get available pipelines for camera stream processing"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{self.backend_url}/api/camera-stream/v1/camera-stream/pipelines",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                pipelines = response.json()
                logger.info(f"✅ Found {len(pipelines.get('pipelines', []))} available pipelines")
                return pipelines
            else:
                logger.error(f"❌ Failed to get pipelines: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Pipeline fetch error: {e}")
            return None

    async def create_test_pipeline(self):
        """Create a test pipeline suitable for real-time processing"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            pipeline_data = {
                "name": "Real-time Test Pipeline",
                "description": "Test pipeline for camera stream integration",
                "components": [
                    {
                        "name": "Resize to 640x480",
                        "component_type": "resize",
                        "parameters": {
                            "width": 640,
                            "height": 480
                        }
                    },
                    {
                        "name": "AI Object Detection",
                        "component_type": "ai_detection",
                        "parameters": {
                            "model_name": "yolo11n",
                            "confidence_threshold": 0.5
                        }
                    }
                ]
            }
            
            response = requests.post(
                f"{self.backend_url}/api/pipelines/",
                headers=headers,
                json=pipeline_data,
                timeout=10
            )
            
            if response.status_code == 200:
                pipeline = response.json()
                logger.info(f"✅ Created test pipeline: {pipeline['id']}")
                return pipeline
            else:
                logger.error(f"❌ Failed to create pipeline: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Pipeline creation error: {e}")
            return None

    def create_test_frame(self):
        """Create a test image frame for processing"""
        # Create a simple test image
        image = Image.new('RGB', (800, 600), color='blue')
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        img_bytes = img_buffer.getvalue()
        
        return base64.b64encode(img_bytes).decode('utf-8')

    async def test_websocket_streaming(self, pipeline_id):
        """Test WebSocket streaming with pipeline processing"""
        try:
            websocket_url = f"{self.websocket_url}/v1/ws/camera-stream/test_camera"
            
            async with websockets.connect(websocket_url) as websocket:
                logger.info("✅ WebSocket connection established")
                
                # Send test frame
                frame_data = self.create_test_frame()
                message = {
                    "type": "frame",
                    "frame_data": frame_data,
                    "pipeline_id": pipeline_id,
                    "timestamp_ms": int(time.time() * 1000),
                    "width": 800,
                    "height": 600,
                    "processing_params": {
                        "model_name": "yolo11n"
                    }
                }
                
                await websocket.send(json.dumps(message))
                logger.info("✅ Test frame sent via WebSocket")
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    result = json.loads(response)
                    logger.info(f"✅ Received processing result: {result}")
                    return True
                except asyncio.TimeoutError:
                    logger.error("❌ Timeout waiting for processing result")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ WebSocket streaming error: {e}")
            return False

    async def test_http_frame_processing(self, pipeline_id):
        """Test HTTP endpoint for single frame processing"""
        try:
            # Create test image file
            image = Image.new('RGB', (640, 480), color='red')
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            
            files = {"file": ("test.jpg", img_buffer, "image/jpeg")}
            data = {
                "pipeline_id": pipeline_id,
                "source_id": "test_camera_http"
            }
            
            response = requests.post(
                f"{self.backend_url}/api/camera-stream/v1/camera-stream/test-frame",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ HTTP frame processing successful: {result}")
                return True
            else:
                logger.error(f"❌ HTTP frame processing failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ HTTP frame processing error: {e}")
            return False

    async def validate_integration(self):
        """Run comprehensive validation of camera stream integration"""
        logger.info("🧪 Starting Camera Stream Integration Validation")
        
        # Step 1: Authentication
        if not await self.authenticate():
            return False
        
        # Step 2: Get available pipelines
        pipelines = await self.get_available_pipelines()
        if not pipelines:
            logger.warning("⚠️ No existing pipelines found, creating test pipeline")
            test_pipeline = await self.create_test_pipeline()
            if not test_pipeline:
                return False
            pipeline_id = test_pipeline["id"]
        else:
            # Use first available pipeline
            pipeline_list = pipelines.get("pipelines", [])
            if pipeline_list:
                pipeline_id = pipeline_list[0]["id"]
                logger.info(f"✅ Using existing pipeline: {pipeline_id}")
            else:
                logger.error("❌ No suitable pipelines found")
                return False
        
        # Step 3: Test HTTP frame processing
        logger.info("\n🔍 Testing HTTP frame processing...")
        http_success = await self.test_http_frame_processing(pipeline_id)
        
        # Step 4: Test WebSocket streaming
        logger.info("\n🔍 Testing WebSocket streaming...")
        websocket_success = await self.test_websocket_streaming(pipeline_id)
        
        # Summary
        logger.info(f"\n📊 Validation Results:")
        logger.info(f"  HTTP Processing: {'✅ PASS' if http_success else '❌ FAIL'}")
        logger.info(f"  WebSocket Streaming: {'✅ PASS' if websocket_success else '❌ FAIL'}")
        
        overall_success = http_success and websocket_success
        if overall_success:
            logger.info("🎉 Camera stream integration validation successful!")
        else:
            logger.error("💥 Camera stream integration validation failed!")
        
        return overall_success

async def main():
    """Main validation function"""
    validator = CameraStreamValidator()
    success = await validator.validate_integration()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        exit(1)
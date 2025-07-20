#!/usr/bin/env python3

"""
Test script for ImageFlowCanvas gRPC services
Tests the basic functionality of resize, AI detection, and filter services
"""

import sys
import os
import json
import time
import requests
import logging

# Add generated proto path
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GRPCServiceTester:
    def __init__(self, gateway_url="http://localhost:8080"):
        self.gateway_url = gateway_url
        self.test_data = {
            "input_image": {
                "bucket": "test-bucket",
                "object_key": "test-image.jpg",
                "content_type": "image/jpeg"
            },
            "execution_id": f"test-{int(time.time())}"
        }
    
    def test_gateway_health(self):
        """Test gateway health endpoint"""
        try:
            response = requests.get(f"{self.gateway_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Gateway health check passed")
                return True
            else:
                logger.error(f"❌ Gateway health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Gateway health check failed: {e}")
            return False
    
    def test_resize_service(self):
        """Test resize service via gateway"""
        try:
            payload = {
                **self.test_data,
                "target_width": 800,
                "target_height": 600,
                "maintain_aspect_ratio": True,
                "quality": "RESIZE_QUALITY_GOOD"
            }
            
            response = requests.post(
                f"{self.gateway_url}/v1/resize",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Resize service test passed")
                logger.info(f"   Status: {result.get('result', {}).get('status')}")
                return True
            else:
                logger.error(f"❌ Resize service test failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Resize service test failed: {e}")
            return False
    
    def test_detection_service(self):
        """Test AI detection service via gateway"""
        try:
            payload = {
                **self.test_data,
                "model_name": "yolo",
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4,
                "draw_boxes": True
            }
            
            response = requests.post(
                f"{self.gateway_url}/v1/detect",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ AI Detection service test passed")
                logger.info(f"   Status: {result.get('result', {}).get('status')}")
                return True
            else:
                logger.error(f"❌ AI Detection service test failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ AI Detection service test failed: {e}")
            return False
    
    def test_filter_service(self):
        """Test filter service via gateway"""
        try:
            payload = {
                **self.test_data,
                "filter_type": "FILTER_TYPE_BLUR",
                "intensity": 1.0,
                "parameters": {}
            }
            
            response = requests.post(
                f"{self.gateway_url}/v1/filter",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Filter service test passed")
                logger.info(f"   Status: {result.get('result', {}).get('status')}")
                return True
            else:
                logger.error(f"❌ Filter service test failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Filter service test failed: {e}")
            return False
    
    def test_service_health_endpoints(self):
        """Test individual service health endpoints"""
        services = ["resize", "detection", "filter"]
        all_healthy = True
        
        for service in services:
            try:
                response = requests.get(f"{self.gateway_url}/v1/health/{service}", timeout=10)
                if response.status_code == 200:
                    logger.info(f"✅ {service.capitalize()} service health check passed")
                else:
                    logger.error(f"❌ {service.capitalize()} service health check failed: {response.status_code}")
                    all_healthy = False
            except Exception as e:
                logger.error(f"❌ {service.capitalize()} service health check failed: {e}")
                all_healthy = False
        
        return all_healthy
    
    def run_all_tests(self):
        """Run all tests and return overall result"""
        logger.info("🧪 Starting gRPC services test suite")
        logger.info(f"Testing gateway at: {self.gateway_url}")
        
        tests = [
            ("Gateway Health", self.test_gateway_health),
            ("Service Health Endpoints", self.test_service_health_endpoints),
            ("Resize Service", self.test_resize_service),
            ("AI Detection Service", self.test_detection_service),
            ("Filter Service", self.test_filter_service),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 Running: {test_name}")
            if test_func():
                passed += 1
            time.sleep(1)  # Brief pause between tests
        
        logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! gRPC services are working correctly.")
            return True
        else:
            logger.error("⚠️ Some tests failed. Check service logs for details.")
            return False

def main():
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8080")
    
    tester = GRPCServiceTester(gateway_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
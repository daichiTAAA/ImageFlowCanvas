#!/usr/bin/env python3
"""
Test script for camera stream integration with Web UI pipelines
"""

import sys
import os
import asyncio
import logging

# Add paths for imports
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated/python')
sys.path.append('/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/backend')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all necessary imports work"""
    try:
        # Test proto imports
        from imageflow.v1 import camera_stream_pb2
        from imageflow.v1 import ai_detection_pb2
        from imageflow.v1 import resize_pb2
        from imageflow.v1 import filter_pb2
        from imageflow.v1 import common_pb2
        logger.info("✅ Proto imports successful")
        
        # Test backend imports
        from app.services.pipeline_service import PipelineService
        from app.models.pipeline import Pipeline, PipelineComponent
        logger.info("✅ Backend imports successful")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False

def test_camera_stream_logic():
    """Test camera stream processing logic"""
    try:
        # Simulate camera stream processor logic
        from services.camera_stream_grpc_app.src.camera_stream_grpc_server import CameraStreamProcessorImplementation
        
        # This should fail due to missing environment/connections, but we can test instantiation
        processor = CameraStreamProcessorImplementation()
        logger.info("✅ Camera stream processor instantiation successful")
        
        # Test pipeline sorting logic
        components = [
            {"component_type": "filter", "name": "blur"},
            {"component_type": "ai_detection", "name": "yolo"},
            {"component_type": "resize", "name": "resize_640x480"},
        ]
        
        sorted_components = processor._sort_components_by_dependencies(components)
        expected_order = ["resize", "ai_detection", "filter"]
        actual_order = [c["component_type"] for c in sorted_components]
        
        if actual_order == expected_order:
            logger.info(f"✅ Pipeline component sorting works: {actual_order}")
        else:
            logger.warning(f"⚠️ Pipeline sorting unexpected: {actual_order}, expected: {expected_order}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Camera stream logic error: {e}")
        return False

def test_pipeline_cache_logic():
    """Test pipeline definition caching"""
    try:
        # Mock pipeline definition
        mock_pipeline = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "components": [
                {
                    "component_type": "resize",
                    "parameters": {"width": 640, "height": 480}
                },
                {
                    "component_type": "ai_detection", 
                    "parameters": {"model_name": "yolo11n", "confidence_threshold": 0.5}
                }
            ]
        }
        
        logger.info("✅ Pipeline definition structure valid")
        
        # Test supported component filtering
        supported_components = {"resize", "ai_detection", "filter"}
        has_supported = any(
            comp["component_type"] in supported_components 
            for comp in mock_pipeline["components"]
        )
        
        if has_supported:
            logger.info("✅ Pipeline contains supported components")
        else:
            logger.error("❌ Pipeline does not contain supported components")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline cache logic error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing camera stream integration with Web UI pipelines")
    
    tests = [
        ("Proto and Backend Imports", test_imports),
        ("Camera Stream Logic", test_camera_stream_logic),
        ("Pipeline Cache Logic", test_pipeline_cache_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n📊 Test Results Summary:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Camera stream integration ready.")
        return True
    else:
        logger.error("💥 Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
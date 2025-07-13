#!/usr/bin/env python3
"""
Test the YOLO11 setup process without actually downloading/converting the model.
"""

import tempfile
import os
from pathlib import Path

def test_download_simulation():
    """Test the download part of the setup process."""
    try:
        import requests
        
        # Test if the URL is accessible
        url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
        print(f"Testing download URL: {url}")
        
        response = requests.head(url, allow_redirects=True, timeout=10)
        if response.status_code == 200:
            print("✅ YOLO11n.pt download URL is accessible")
            size = response.headers.get('Content-Length', 'unknown')
            print(f"   File size: {size} bytes")
            return True
        else:
            print(f"❌ YOLO11n.pt URL returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing download: {e}")
        return False

def test_setup_script_structure():
    """Test that the setup script is properly structured."""
    try:
        script_path = Path(__file__).parent.parent / "scripts" / "setup-yolo11.py"
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        required_functions = [
            'download_yolo11_pt',
            'convert_pt_to_onnx', 
            'setup_yolo11'
        ]
        
        for func in required_functions:
            if f"def {func}" in content:
                print(f"✅ Function {func} found in setup script")
            else:
                print(f"❌ Function {func} not found in setup script")
                return False
        
        # Check for proper imports
        required_imports = ['requests', 'ultralytics', 'tempfile', 'os']
        for imp in required_imports:
            if imp in content:
                print(f"✅ Import {imp} found in setup script")
            else:
                print(f"❌ Import {imp} not found in setup script")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing setup script structure: {e}")
        return False

def test_target_directories():
    """Test that target directories exist or can be created."""
    try:
        project_root = Path(__file__).parent.parent
        models_dir = project_root / "models" / "yolo" / "1"
        
        if models_dir.exists():
            print("✅ Target model directory exists")
        else:
            print("❌ Target model directory does not exist")
            return False
        
        # Test if we can write to the directory (create a test file)
        test_file = models_dir / "test_write.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✅ Target directory is writable")
        except Exception as e:
            print(f"❌ Target directory is not writable: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing target directories: {e}")
        return False

def test_triton_config_compatibility():
    """Test that Triton config is compatible with YOLO11."""
    try:
        config_path = Path(__file__).parent.parent / "models" / "yolo" / "config.pbtxt"
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check for YOLO11-compatible configuration
        checks = [
            ('name: "yolo"', "Model name"),
            ('platform: "onnxruntime_onnx"', "ONNX platform"),
            ('dims: [ 3, 640, 640 ]', "Input dimensions"),
            ('dims: [ 84, 8400 ]', "Output dimensions"),
        ]
        
        for check, desc in checks:
            if check in content:
                print(f"✅ {desc} configured correctly")
            else:
                print(f"❌ {desc} not configured correctly")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing Triton config: {e}")
        return False

def main():
    """Run all setup tests."""
    print("🧪 Testing YOLO11 setup process...\n")
    
    tests = [
        ("Download URL", test_download_simulation),
        ("Setup Script Structure", test_setup_script_structure),
        ("Target Directories", test_target_directories),
        ("Triton Config", test_triton_config_compatibility),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n📊 Setup Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ YOLO11 setup process is ready!")
        print("\n🚀 To complete the setup:")
        print("1. Install dependencies: pip install -r backend/requirements.txt")
        print("2. Run setup script: python scripts/setup-yolo11.py")
        return True
    else:
        print("❌ Some setup tests failed. Please review the configuration.")
        return False

if __name__ == "__main__":
    main()
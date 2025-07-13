#!/usr/bin/env python3
"""
Simple test to verify YOLO11 changes are working correctly.
"""

import sys
import json
from pathlib import Path

def test_component_api():
    """Test that the component API has been updated to use YOLO11."""
    try:
        # Test components.py
        components_file = Path(__file__).parent.parent / "backend" / "app" / "api" / "components.py"
        with open(components_file, 'r') as f:
            content = f.read()
        
        # Check that yolo11 is the default and only option
        if '"default": "yolo11"' in content:
            print("✅ Component API default model updated to yolo11")
        else:
            print("❌ Component API default model not updated")
            return False
            
        if '"options": ["yolo11"]' in content:
            print("✅ Component API options updated to only include yolo11")
        else:
            print("❌ Component API options not updated correctly")
            return False
            
        # Check that old YOLO versions are removed
        if 'yolo_v5' in content or 'yolo_v8' in content:
            print("❌ Old YOLO versions still present in component API")
            return False
        else:
            print("✅ Old YOLO versions removed from component API")
            
        return True
    except Exception as e:
        print(f"❌ Error testing component API: {e}")
        return False

def test_execution_worker():
    """Test that the execution worker has been updated."""
    try:
        worker_file = Path(__file__).parent.parent / "backend" / "app" / "services" / "execution_worker.py"
        with open(worker_file, 'r') as f:
            content = f.read()
        
        if '"model": "yolo11"' in content:
            print("✅ Execution worker updated to use yolo11")
            return True
        else:
            print("❌ Execution worker not updated")
            return False
    except Exception as e:
        print(f"❌ Error testing execution worker: {e}")
        return False

def test_requirements():
    """Test that requirements.txt includes ultralytics."""
    try:
        req_file = Path(__file__).parent.parent / "backend" / "requirements.txt"
        with open(req_file, 'r') as f:
            content = f.read()
        
        if 'ultralytics' in content:
            print("✅ ultralytics added to requirements.txt")
            return True
        else:
            print("❌ ultralytics not found in requirements.txt")
            return False
    except Exception as e:
        print(f"❌ Error testing requirements: {e}")
        return False

def test_documentation():
    """Test that documentation has been updated."""
    try:
        # Test model README
        model_readme = Path(__file__).parent.parent / "models" / "yolo" / "1" / "README.md"
        with open(model_readme, 'r') as f:
            content = f.read()
        
        if 'YOLO11' in content:
            print("✅ Model README updated to YOLO11")
        else:
            print("❌ Model README not updated")
            return False
            
        # Test main README
        main_readme = Path(__file__).parent.parent / "README.md"
        with open(main_readme, 'r') as f:
            content = f.read()
        
        if 'setup-yolo11.py' in content:
            print("✅ Main README updated with YOLO11 setup instructions")
        else:
            print("❌ Main README not updated")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Error testing documentation: {e}")
        return False

def test_setup_script():
    """Test that the setup script exists and is executable."""
    try:
        script_file = Path(__file__).parent.parent / "scripts" / "setup-yolo11.py"
        
        if script_file.exists():
            print("✅ YOLO11 setup script exists")
        else:
            print("❌ YOLO11 setup script not found")
            return False
            
        # Check if executable
        import os
        if os.access(script_file, os.X_OK):
            print("✅ YOLO11 setup script is executable")
        else:
            print("❌ YOLO11 setup script is not executable")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Error testing setup script: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing YOLO11 migration changes...\n")
    
    tests = [
        ("Component API", test_component_api),
        ("Execution Worker", test_execution_worker),
        ("Requirements", test_requirements),
        ("Documentation", test_documentation),
        ("Setup Script", test_setup_script),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! YOLO11 migration is complete.")
        return True
    else:
        print("❌ Some tests failed. Please review the changes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Script to download YOLO11n.pt model and convert it to ONNX format for Triton Inference Server.
"""

import os
import sys
import requests
import tempfile
from pathlib import Path


def download_yolo11_pt(url: str, output_path: str) -> bool:
    """Download YOLO11n.pt model from the specified URL."""
    try:
        print(f"Downloading YOLO11n.pt from {url}...")
        response = requests.get(url, stream=True, allow_redirects=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded YOLO11n.pt to {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading YOLO11n.pt: {e}")
        return False


def convert_pt_to_onnx(pt_path: str, onnx_path: str) -> bool:
    """Convert YOLO11n.pt to ONNX format."""
    try:
        # Import ultralytics (will need to be installed)
        from ultralytics import YOLO

        print(f"Loading YOLO11 model from {pt_path}...")
        model = YOLO(pt_path)

        print(f"Converting to ONNX format...")
        model.export(format="onnx", imgsz=640, dynamic=False)

        # The export creates a file with .onnx extension in the same directory
        pt_dir = os.path.dirname(pt_path)
        pt_name = os.path.splitext(os.path.basename(pt_path))[0]
        exported_onnx = os.path.join(pt_dir, f"{pt_name}.onnx")

        if os.path.exists(exported_onnx):
            # Move to the target location
            os.makedirs(os.path.dirname(onnx_path), exist_ok=True)
            os.rename(exported_onnx, onnx_path)
            print(f"Converted ONNX model saved to {onnx_path}")
            return True
        else:
            print("Error: ONNX file was not created")
            return False
    except ImportError as e:
        print(f"Error importing ultralytics: {e}")
        print("This might be due to missing system dependencies.")
        print("Please check if OpenGL libraries are installed.")
        return False
    except Exception as e:
        print(f"Error converting to ONNX: {e}")
        return False


def setup_yolo11():
    """Main function to set up YOLO11 model."""
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    models_dir = project_root / "models" / "yolo" / "1"

    # YOLO11n.pt download URL
    yolo11_url = (
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
    )

    # Temporary path for downloaded .pt file
    temp_pt_path = tempfile.mktemp(suffix=".pt")

    # Final ONNX path
    onnx_path = models_dir / "model.onnx"

    try:
        # Step 1: Download YOLO11n.pt
        if not download_yolo11_pt(yolo11_url, temp_pt_path):
            return False

        # Step 2: Convert to ONNX
        if not convert_pt_to_onnx(temp_pt_path, str(onnx_path)):
            return False

        print(f"\n✅ YOLO11 setup completed successfully!")
        print(f"ONNX model is ready at: {onnx_path}")
        print("\nNext steps:")
        print("1. Make sure Triton Inference Server is running")
        print("2. The model will be automatically loaded by Triton")
        print("3. You can now use YOLO11 for object detection")

        return True

    finally:
        # Clean up temporary file
        if os.path.exists(temp_pt_path):
            os.remove(temp_pt_path)


if __name__ == "__main__":
    success = setup_yolo11()
    sys.exit(0 if success else 1)

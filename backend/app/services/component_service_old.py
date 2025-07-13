import asyncio
import json
import os
import logging
from typing import Dict, Any, List
from app.services.file_service import FileService
from app.models.execution import OutputFile
import uuid

logger = logging.getLogger(__name__)

class ComponentService:
    """
    Component service for ImageFlowCanvas.
    
    Note: According to the architecture design, this service should NOT perform
    direct image processing. Image processing is delegated to Argo Workflows
    which execute containerized processing services.
    
    This service only handles component metadata and coordination.
    """
    def __init__(self):
        self.file_service = FileService()
        # Remove direct processing dependencies - these are now handled by Argo Workflows
        # self.triton_client = TritonYOLOClient(...)  # REMOVED
    
    async def get_component_metadata(self, component_type: str) -> Dict[str, Any]:
        """Get metadata for a component type (parameters, capabilities, etc.)"""
        component_metadata = {
            "resize": {
                "name": "Image Resize",
                "description": "Resize images to specified dimensions",
                "parameters": {
                    "width": {"type": "integer", "default": 800, "min": 1, "max": 4096},
                    "height": {"type": "integer", "default": 600, "min": 1, "max": 4096},
                    "maintain_aspect": {"type": "boolean", "default": True}
                },
                "input_formats": ["jpg", "jpeg", "png", "bmp", "tiff"],
                "output_formats": ["jpg", "png"],
                "container_image": "imageflow/resize-app:latest"
            },
            "ai_detection": {
                "name": "AI Object Detection",
                "description": "Detect objects in images using AI models",
                "parameters": {
                    "model": {"type": "string", "default": "yolo11n.pt", "options": ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt"]},
                    "confidence": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
                    "draw_boxes": {"type": "boolean", "default": True}
                },
                "input_formats": ["jpg", "jpeg", "png"],
                "output_formats": ["jpg", "json"],
                "container_image": "imageflow/object-detection-app:latest"
            },
            "filter": {
                "name": "Image Filter",
                "description": "Apply filters and effects to images",
                "parameters": {
                    "filter_type": {"type": "string", "default": "blur", "options": ["blur", "sharpen", "edge", "emboss", "grayscale"]},
                    "intensity": {"type": "float", "default": 1.0, "min": 0.0, "max": 5.0}
                },
                "input_formats": ["jpg", "jpeg", "png", "bmp"],
                "output_formats": ["jpg", "png"],
                "container_image": "imageflow/filter-app:latest"
            }
        }
        
        return component_metadata.get(component_type, {})
    
    async def validate_component_parameters(self, component_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize component parameters"""
        metadata = await self.get_component_metadata(component_type)
        param_definitions = metadata.get("parameters", {})
        
        validated_params = {}
        
        for param_name, param_def in param_definitions.items():
            param_type = param_def.get("type")
            default_value = param_def.get("default")
            
            # Get value from parameters or use default
            value = parameters.get(param_name, default_value)
            
            # Type validation and conversion
            if param_type == "integer":
                try:
                    value = int(value)
                    if "min" in param_def:
                        value = max(value, param_def["min"])
                    if "max" in param_def:
                        value = min(value, param_def["max"])
                except (ValueError, TypeError):
                    value = default_value
            elif param_type == "float":
                try:
                    value = float(value)
                    if "min" in param_def:
                        value = max(value, param_def["min"])
                    if "max" in param_def:
                        value = min(value, param_def["max"])
                except (ValueError, TypeError):
                    value = default_value
            elif param_type == "boolean":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            elif param_type == "string":
                if "options" in param_def and value not in param_def["options"]:
                    value = default_value
            
            validated_params[param_name] = value
        
        return validated_params
    
    async def get_available_components(self) -> List[Dict[str, Any]]:
        """Get list of all available components"""
        component_types = ["resize", "ai_detection", "filter"]
        components = []
        
        for component_type in component_types:
            metadata = await self.get_component_metadata(component_type)
            if metadata:
                components.append({
                    "type": component_type,
                    **metadata
                })
        
        return components
    
    # REMOVED: All direct processing methods have been removed
    # Image processing is now handled by Argo Workflows executing containerized services
    # 
    # The following methods were removed:
    # - async def process_component(...)
    # - async def _process_object_detection(...)
    # - async def _process_resize(...)
    # - async def _process_filter(...)
    #
    # These processing capabilities are now provided by:
    # - services/resize-app/ (for resize operations)
    # - services/object-detection-app/ (for AI detection)
    # - services/filter-app/ (for image filtering)
    #
    # The backend now only coordinates and delegates to Argo Workflows
        """物体検出の処理（Triton Inference Server使用）"""
        output_files = []
        
        confidence_threshold = parameters.get("confidence", 0.5)
        
        for file_id in input_files:
            try:
                # 入力ファイルをダウンロード
                file_data, filename, content_type = await self.file_service.download_file(file_id)
                
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_input:
                    tmp_input.write(file_data.read())
                    tmp_input_path = tmp_input.name
                
                # 出力ファイルのパス
                output_filename = f"detected_{os.path.splitext(filename)[0]}.jpg"
                tmp_output_path = tempfile.mktemp(suffix=".jpg")
                
                try:
                    # Tritonを使用して物体検出を実行
                    logger.info(f"Running object detection on {filename} using Triton")
                    detections = await self.triton_client.detect_objects(
                        tmp_input_path, 
                        confidence_threshold=confidence_threshold
                    )
                    
                    # 検出結果を画像に描画
                    await self.triton_client.draw_detections(tmp_input_path, tmp_output_path, detections)
                    
                    # 検出結果をJSONとして保存
                    result_json_path = tempfile.mktemp(suffix=".json")
                    detection_result = {
                        "input_file": filename,
                        "detections_count": len(detections),
                        "detections": detections,
                        "confidence_threshold": confidence_threshold,
                        "model_type": "yolo11_triton"
                    }
                    
                    with open(result_json_path, 'w') as f:
                        json.dump(detection_result, f, indent=2)
                    
                    # 結果画像をアップロード
                    with open(tmp_output_path, 'rb') as output_file:
                        from fastapi import UploadFile
                        from io import BytesIO
                        
                        upload_file = UploadFile(
                            filename=output_filename,
                            file=BytesIO(output_file.read()),
                            content_type="image/jpeg"
                        )
                        
                        output_file_id = await self.file_service.upload_file(upload_file)
                        
                        output_file_obj = OutputFile(
                            file_id=output_file_id,
                            filename=output_filename,
                            download_url=f"/api/v1/files/{output_file_id}/download",
                            file_size=os.path.getsize(tmp_output_path)
                        )
                        output_files.append(output_file_obj)
                    
                    # 検出結果JSONもアップロード
                    with open(result_json_path, 'rb') as json_file:
                        json_filename = f"detection_results_{os.path.splitext(filename)[0]}.json"
                        upload_json = UploadFile(
                            filename=json_filename,
                            file=BytesIO(json_file.read()),
                            content_type="application/json"
                        )
                        
                        json_file_id = await self.file_service.upload_file(upload_json)
                        
                        json_output_obj = OutputFile(
                            file_id=json_file_id,
                            filename=json_filename,
                            download_url=f"/api/v1/files/{json_file_id}/download",
                            file_size=os.path.getsize(result_json_path)
                        )
                        output_files.append(json_output_obj)
                    
                    logger.info(f"Object detection completed for {filename}: {len(detections)} objects detected")
                
                finally:
                    # 一時ファイルをクリーンアップ
                    if os.path.exists(tmp_input_path):
                        os.unlink(tmp_input_path)
                    if os.path.exists(tmp_output_path):
                        os.unlink(tmp_output_path)
                    if 'result_json_path' in locals() and os.path.exists(result_json_path):
                        os.unlink(result_json_path)
                        
            except Exception as e:
                logger.error(f"Error processing file {file_id}: {e}")
                continue
        
        return output_files

    
    async def _process_resize(self, input_files: List[str], parameters: Dict[str, Any]) -> List[OutputFile]:
        """リサイズの処理"""
        output_files = []
        
        width = parameters.get("width", 800)
        height = parameters.get("height", 600)
        
        for file_id in input_files:
            try:
                # 入力ファイルをダウンロード
                file_data, filename, content_type = await self.file_service.download_file(file_id)
                
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_input:
                    tmp_input.write(file_data.read())
                    tmp_input_path = tmp_input.name
                
                # 出力ファイルのパス
                output_filename = f"resized_{width}x{height}_{filename}"
                tmp_output_path = tempfile.mktemp(suffix=os.path.splitext(filename)[1])
                
                try:
                    # リサイズ処理
                    await self._simulate_resize(tmp_input_path, tmp_output_path, width, height)
                    
                    # 結果ファイルをアップロード
                    with open(tmp_output_path, 'rb') as output_file:
                        from fastapi import UploadFile
                        from io import BytesIO
                        
                        upload_file = UploadFile(
                            filename=output_filename,
                            file=BytesIO(output_file.read()),
                            content_type=content_type
                        )
                        
                        output_file_id = await self.file_service.upload_file(upload_file)
                        
                        output_file_obj = OutputFile(
                            file_id=output_file_id,
                            filename=output_filename,
                            download_url=f"/api/v1/files/{output_file_id}/download",
                            file_size=os.path.getsize(tmp_output_path)
                        )
                        output_files.append(output_file_obj)
                
                finally:
                    # 一時ファイルをクリーンアップ
                    if os.path.exists(tmp_input_path):
                        os.unlink(tmp_input_path)
                    if os.path.exists(tmp_output_path):
                        os.unlink(tmp_output_path)
                        
            except Exception as e:
                logger.error(f"Error processing file {file_id}: {e}")
                continue
        
        return output_files
    
    async def _simulate_resize(self, input_path: str, output_path: str, width: int, height: int):
        """リサイズをシミュレート"""
        try:
            import cv2
            
            img = cv2.imread(input_path)
            if img is None:
                raise Exception(f"Could not read image: {input_path}")
            
            # リサイズ
            resized_img = cv2.resize(img, (width, height))
            
            # 結果を保存
            cv2.imwrite(output_path, resized_img)
            logger.info(f"Resize simulation completed: {output_path}")
            
        except Exception as e:
            logger.error(f"Error in resize simulation: {e}")
            # フォールバック: 元の画像をコピー
            import shutil
            shutil.copy2(input_path, output_path)
    
    async def _process_filter(self, input_files: List[str], parameters: Dict[str, Any]) -> List[OutputFile]:
        """フィルタ処理"""
        output_files = []
        
        filter_type = parameters.get("filter_type", "blur")
        
        for file_id in input_files:
            try:
                # 入力ファイルをダウンロード
                file_data, filename, content_type = await self.file_service.download_file(file_id)
                
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_input:
                    tmp_input.write(file_data.read())
                    tmp_input_path = tmp_input.name
                
                # 出力ファイルのパス
                output_filename = f"{filter_type}_{filename}"
                tmp_output_path = tempfile.mktemp(suffix=os.path.splitext(filename)[1])
                
                try:
                    # フィルタ処理
                    await self._simulate_filter(tmp_input_path, tmp_output_path, filter_type)
                    
                    # 結果ファイルをアップロード
                    with open(tmp_output_path, 'rb') as output_file:
                        from fastapi import UploadFile
                        from io import BytesIO
                        
                        upload_file = UploadFile(
                            filename=output_filename,
                            file=BytesIO(output_file.read()),
                            content_type=content_type
                        )
                        
                        output_file_id = await self.file_service.upload_file(upload_file)
                        
                        output_file_obj = OutputFile(
                            file_id=output_file_id,
                            filename=output_filename,
                            download_url=f"/api/v1/files/{output_file_id}/download",
                            file_size=os.path.getsize(tmp_output_path)
                        )
                        output_files.append(output_file_obj)
                
                finally:
                    # 一時ファイルをクリーンアップ
                    if os.path.exists(tmp_input_path):
                        os.unlink(tmp_input_path)
                    if os.path.exists(tmp_output_path):
                        os.unlink(tmp_output_path)
                        
            except Exception as e:
                logger.error(f"Error processing file {file_id}: {e}")
                continue
        
        return output_files
    
    async def _simulate_filter(self, input_path: str, output_path: str, filter_type: str):
        """フィルタをシミュレート"""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(input_path)
            if img is None:
                raise Exception(f"Could not read image: {input_path}")
            
            # フィルタタイプに応じて処理
            if filter_type == "blur":
                filtered_img = cv2.GaussianBlur(img, (15, 15), 0)
            elif filter_type == "sharpen":
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                filtered_img = cv2.filter2D(img, -1, kernel)
            elif filter_type == "edge":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                filtered_img = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            else:
                filtered_img = img  # デフォルトは元画像
            
            # 結果を保存
            cv2.imwrite(output_path, filtered_img)
            logger.info(f"Filter simulation completed: {output_path}")
            
        except Exception as e:
            logger.error(f"Error in filter simulation: {e}")
            # フォールバック: 元の画像をコピー
            import shutil
            shutil.copy2(input_path, output_path)
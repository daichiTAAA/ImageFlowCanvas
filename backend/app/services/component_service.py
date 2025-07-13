import asyncio
import json
import os
import tempfile
import subprocess
from typing import Dict, Any, List
from app.services.file_service import FileService
from app.services.triton_client import TritonYOLOClient
from app.models.execution import OutputFile
import uuid
import logging

logger = logging.getLogger(__name__)

class ComponentService:
    def __init__(self):
        self.file_service = FileService()
        self.triton_client = TritonYOLOClient(
            triton_url=os.getenv("TRITON_URL", "localhost:8000"),
            model_name=os.getenv("YOLO_MODEL_NAME", "yolo"),
            model_version=os.getenv("YOLO_MODEL_VERSION", "1")
        )
    
    async def process_component(self, component_type: str, input_files: List[str], parameters: Dict[str, Any]) -> List[OutputFile]:
        """コンポーネントを処理して結果ファイルを生成"""
        try:
            if component_type == "ai_detection" or component_type == "object_detection":
                return await self._process_object_detection(input_files, parameters)
            elif component_type == "resize":
                return await self._process_resize(input_files, parameters)
            elif component_type == "filter":
                return await self._process_filter(input_files, parameters)
            else:
                logger.warning(f"Unknown component type: {component_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error processing component {component_type}: {e}")
            return []
    
    async def _process_object_detection(self, input_files: List[str], parameters: Dict[str, Any]) -> List[OutputFile]:
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
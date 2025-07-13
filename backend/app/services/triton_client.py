import numpy as np
import cv2
import logging
from typing import List, Dict, Any, Tuple
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    import tritonclient.http as httpclient
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False
    logger.warning("Triton client not available, using mock detection")

class TritonYOLOClient:
    def __init__(self, 
                 triton_url: str = "localhost:8000", 
                 model_name: str = "yolo",
                 model_version: str = "1"):
        self.triton_url = triton_url
        self.model_name = model_name
        self.model_version = model_version
        self.triton_available = TRITON_AVAILABLE
        
        if self.triton_available:
            try:
                self.triton_client = httpclient.InferenceServerClient(url=triton_url)
                self._check_model_ready()
            except Exception as e:
                logger.warning(f"Could not connect to Triton server: {e}")
                self.triton_available = False
        
        # COCO クラス名（YOLO用）
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
    
    def _check_model_ready(self):
        """モデルの準備状況を確認"""
        if not self.triton_available:
            return False
        
        try:
            model_ready = self.triton_client.is_model_ready(
                model_name=self.model_name,
                model_version=self.model_version
            )
            if not model_ready:
                logger.warning(f"Model {self.model_name} version {self.model_version} is not ready")
                return False
            
            logger.info(f"Triton model {self.model_name} is ready")
            return True
        except Exception as e:
            logger.warning(f"Could not check model readiness: {e}")
            return False
    
    async def detect_objects(self, 
                           image_path: str, 
                           confidence_threshold: float = 0.5,
                           iou_threshold: float = 0.45) -> List[Dict[str, Any]]:
        """物体検出を実行"""
        if not self.triton_available:
            return await self._mock_detect_objects(image_path, confidence_threshold)
        
        try:
            return await self._triton_detect_objects(image_path, confidence_threshold, iou_threshold)
        except Exception as e:
            logger.error(f"Triton detection failed, falling back to mock: {e}")
            return await self._mock_detect_objects(image_path, confidence_threshold)
    
    async def _triton_detect_objects(self, 
                                   image_path: str, 
                                   confidence_threshold: float,
                                   iou_threshold: float) -> List[Dict[str, Any]]:
        """Tritonサーバーを使用した物体検出"""
        # 画像の前処理
        image = cv2.imread(image_path)
        if image is None:
            raise Exception(f"Could not read image: {image_path}")
        
        original_height, original_width = image.shape[:2]
        
        # YOLOの入力形式に変換（640x640）
        input_image = self._preprocess_image(image, (640, 640))
        
        # Triton推論リクエストを作成
        inputs = []
        outputs = []
        
        # 入力テンソル
        inputs.append(httpclient.InferInput('images', input_image.shape, "FP32"))
        inputs[0].set_data_from_numpy(input_image)
        
        # 出力テンソル
        outputs.append(httpclient.InferRequestedOutput('output0'))
        
        # 推論実行
        results = self.triton_client.infer(
            model_name=self.model_name,
            model_version=self.model_version,
            inputs=inputs,
            outputs=outputs
        )
        
        # 結果を取得
        output_data = results.as_numpy('output0')
        
        # 後処理
        detections = self._postprocess_detections(
            output_data, 
            original_width, 
            original_height,
            confidence_threshold,
            iou_threshold
        )
        
        return detections
    
    def _preprocess_image(self, image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """YOLOの入力形式に画像を前処理"""
        # リサイズ（アスペクト比保持）
        h, w = image.shape[:2]
        target_w, target_h = target_size
        
        # アスペクト比を保持してリサイズ
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized_image = cv2.resize(image, (new_w, new_h))
        
        # パディングを追加
        pad_w = (target_w - new_w) // 2
        pad_h = (target_h - new_h) // 2
        
        padded_image = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded_image[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized_image
        
        # 正規化とチャンネル順序変更
        input_image = padded_image.astype(np.float32) / 255.0
        input_image = np.transpose(input_image, (2, 0, 1))  # HWC -> CHW
        input_image = np.expand_dims(input_image, axis=0)  # バッチ次元追加
        
        return input_image
    
    def _postprocess_detections(self, 
                              output_data: np.ndarray,
                              original_width: int,
                              original_height: int,
                              confidence_threshold: float,
                              iou_threshold: float) -> List[Dict[str, Any]]:
        """YOLO出力の後処理"""
        detections = []
        
        # YOLOv8の出力形式を想定
        # output_data shape: [1, 84, 8400] (84 = 4 bbox coords + 80 classes)
        
        if len(output_data.shape) == 3:
            output_data = output_data[0]  # バッチ次元削除
        
        # 転置 [84, 8400] -> [8400, 84]
        if output_data.shape[0] == 84:
            output_data = output_data.T
        
        # 信頼度でフィルタリング
        scores = np.max(output_data[:, 4:], axis=1)
        valid_indices = scores > confidence_threshold
        
        if not np.any(valid_indices):
            return detections
        
        valid_detections = output_data[valid_indices]
        valid_scores = scores[valid_indices]
        
        # クラスIDを取得
        class_ids = np.argmax(valid_detections[:, 4:], axis=1)
        
        # バウンディングボックスの変換（中心座標+幅高さ -> 左上右下）
        boxes = self._convert_boxes(valid_detections[:, :4], original_width, original_height)
        
        # NMS適用
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(), 
            valid_scores.tolist(), 
            confidence_threshold, 
            iou_threshold
        )
        
        if len(indices) > 0:
            for i in indices.flatten():
                x1, y1, x2, y2 = boxes[i]
                confidence = valid_scores[i]
                class_id = class_ids[i]
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
                
                detection = {
                    "class": class_name,
                    "confidence": float(confidence),
                    "bbox": {
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2)
                    }
                }
                detections.append(detection)
        
        return detections
    
    def _convert_boxes(self, boxes: np.ndarray, img_width: int, img_height: int) -> np.ndarray:
        """YOLOボックス形式を変換"""
        # 中心座標+幅高さ -> 左上右下
        converted_boxes = np.zeros_like(boxes)
        
        # 640x640の座標を元画像サイズにスケール
        scale_x = img_width / 640
        scale_y = img_height / 640
        
        center_x = boxes[:, 0] * scale_x
        center_y = boxes[:, 1] * scale_y
        width = boxes[:, 2] * scale_x
        height = boxes[:, 3] * scale_y
        
        converted_boxes[:, 0] = center_x - width / 2  # x1
        converted_boxes[:, 1] = center_y - height / 2  # y1
        converted_boxes[:, 2] = center_x + width / 2   # x2
        converted_boxes[:, 3] = center_y + height / 2  # y2
        
        # 画像境界内にクランプ
        converted_boxes[:, 0] = np.clip(converted_boxes[:, 0], 0, img_width)
        converted_boxes[:, 1] = np.clip(converted_boxes[:, 1], 0, img_height)
        converted_boxes[:, 2] = np.clip(converted_boxes[:, 2], 0, img_width)
        converted_boxes[:, 3] = np.clip(converted_boxes[:, 3], 0, img_height)
        
        return converted_boxes
    
    async def _mock_detect_objects(self, image_path: str, confidence_threshold: float) -> List[Dict[str, Any]]:
        """モック物体検出（Tritonが利用できない場合）"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise Exception(f"Could not read image: {image_path}")
            
            height, width = image.shape[:2]
            
            # ランダムに検出結果をシミュレート
            detections = []
            num_detections = np.random.randint(1, 4)  # 1-3個の物体を検出
            
            available_classes = ['person', 'car', 'cat', 'dog', 'bicycle']
            
            for i in range(num_detections):
                x1 = np.random.randint(0, width // 2)
                y1 = np.random.randint(0, height // 2)
                x2 = np.random.randint(x1 + 50, min(x1 + 200, width))
                y2 = np.random.randint(y1 + 50, min(y1 + 200, height))
                
                confidence = np.random.uniform(confidence_threshold, 0.95)
                class_name = np.random.choice(available_classes)
                
                detection = {
                    "class": class_name,
                    "confidence": float(confidence),
                    "bbox": {
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2)
                    }
                }
                detections.append(detection)
            
            logger.info(f"Mock detection generated {len(detections)} objects")
            return detections
            
        except Exception as e:
            logger.error(f"Error in mock detection: {e}")
            return []
    
    async def draw_detections(self, image_path: str, output_path: str, detections: List[Dict[str, Any]]):
        """検出結果を画像に描画"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise Exception(f"Could not read image: {image_path}")
            
            for detection in detections:
                bbox = detection["bbox"]
                class_name = detection["class"]
                confidence = detection["confidence"]
                
                x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
                
                # バウンディングボックスを描画
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # ラベルを描画
                label = f"{class_name}: {confidence:.2f}"
                cv2.putText(image, label, (x1, y1 - 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 結果を保存
            cv2.imwrite(output_path, image)
            logger.info(f"Detection results drawn and saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            # フォールバック: 元の画像をコピー
            import shutil
            shutil.copy2(image_path, output_path)
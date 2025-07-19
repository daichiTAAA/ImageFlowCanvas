import os
import sys
import logging
import argparse
from minio import Minio
import cv2
import numpy as np
import json
import tritonclient.http as httpclient
from tritonclient.utils import triton_to_np_dtype

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Detect objects in an image from MinIO using Triton Inference Server.")
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--model", default="yolo11n", help="Model name in Triton server")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--draw-boxes", type=bool, default=True, help="Draw bounding boxes on output")
    parser.add_argument("--triton-url", default="triton-server:8000", help="Triton server URL")
    args = parser.parse_args()

    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    triton_url = os.getenv("TRITON_SERVER_URL", args.triton_url)

    local_input = "/tmp/input_image"
    local_output = "/tmp/output_image"

    try:
        # MinIOクライアントの初期化
        client = Minio(minio_endpoint, access_key=minio_access_key, secret_key=minio_secret_key, secure=False)
        logging.info(f"Downloading {args.input_path} from bucket {args.input_bucket}...")
        client.fget_object(args.input_bucket, args.input_path, local_input)

        # Tritonクライアントの初期化
        logging.info(f"Connecting to Triton server at {triton_url}")
        triton_client = httpclient.InferenceServerClient(url=triton_url)
        
        # モデルが利用可能かチェック
        if not triton_client.is_model_ready(args.model):
            raise Exception(f"Model {args.model} is not ready on Triton server")

        # モデル情報を取得
        model_metadata = triton_client.get_model_metadata(args.model)
        model_config = triton_client.get_model_config(args.model)
        
        # 画像の前処理
        logging.info("Preprocessing image...")
        img = cv2.imread(local_input)
        if img is None:
            raise Exception(f"Failed to read image from {local_input}")
        
        original_h, original_w = img.shape[:2]
        
        # YOLOの入力サイズに合わせてリサイズ（通常640x640）
        input_w, input_h = 640, 640
        img_resized = cv2.resize(img, (input_w, input_h))
        
        # RGB変換とnormalization
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        
        # CHWフォーマットに変換 (batch_size, channels, height, width)
        img_input = np.transpose(img_normalized, (2, 0, 1))
        img_input = np.expand_dims(img_input, axis=0)
        
        # Triton推論リクエストの準備
        inputs = []
        outputs = []
        
        input_name = model_metadata.inputs[0].name
        output_name = model_metadata.outputs[0].name
        
        inputs.append(httpclient.InferInput(input_name, img_input.shape, "FP32"))
        inputs[0].set_data_from_numpy(img_input)
        
        outputs.append(httpclient.InferRequestedOutput(output_name))
        
        # 推論実行
        logging.info(f"Running inference with model: {args.model}")
        response = triton_client.infer(args.model, inputs, outputs=outputs)
        
        # 結果の取得
        output_data = response.as_numpy(output_name)
        
        # 後処理: YOLOの出力を解析
        logging.info("Post-processing results...")
        detections = post_process_yolo_output(
            output_data, 
            original_w, 
            original_h, 
            input_w, 
            input_h, 
            args.confidence
        )
        
        # バウンディングボックスを描画
        if args.draw_boxes:
            for detection in detections:
                bbox = detection["bbox"]
                x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
                
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{detection['class']}: {detection['confidence']:.2f}"
                cv2.putText(img, label, (x1, y1 - 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        logging.info(f"Detected {len(detections)} objects")

        # 結果画像を保存
        _, ext = os.path.splitext(args.output_path)
        if not ext:
            ext = ".jpg"
        
        output_file = local_output + ext
        cv2.imwrite(output_file, img)
        logging.info(f"Object detection complete. Result saved to {output_file}")

        # 結果をMinIOにアップロード
        if not client.bucket_exists(args.output_bucket):
            client.make_bucket(args.output_bucket)

        logging.info(f"Uploading {args.output_path} to bucket {args.output_bucket}...")
        client.fput_object(args.output_bucket, args.output_path, output_file)
        logging.info("Upload complete.")

        # 結果をJSON形式で出力
        result_data = {
            "status": "success",
            "input_file": f"{args.input_bucket}/{args.input_path}",
            "output_file": f"{args.output_bucket}/{args.output_path}",
            "model_used": args.model,
            "triton_server": triton_url,
            "detections_count": len(detections),
            "detections": detections,
            "confidence_threshold": args.confidence
        }
        
        # 結果をファイルに保存
        with open("/tmp/result.json", "w") as f:
            json.dump(result_data, f, indent=2)
        
        print(json.dumps(result_data))

    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e)
        }
        logging.error(f"An error occurred: {e}")
        print(json.dumps(error_result))
        sys.exit(1)

def post_process_yolo_output(output, orig_w, orig_h, input_w, input_h, conf_threshold):
    """
    YOLO11の出力を後処理して検出結果を取得
    """
    detections = []
    
    # YOLOの出力形式に応じて調整が必要
    # 一般的なYOLOの出力: [batch_size, num_detections, 85] (x, y, w, h, conf, class_probs...)
    if len(output.shape) == 3:
        output = output[0]  # バッチ次元を削除
    
    # スケールファクター
    scale_x = orig_w / input_w
    scale_y = orig_h / input_h
    
    for detection in output:
        if len(detection) < 5:
            continue
            
        # 座標とconfidenceの取得（YOLOv8/11形式）
        x_center, y_center, width, height = detection[:4]
        confidence = detection[4]
        
        if confidence < conf_threshold:
            continue
        
        # クラス確率の取得（最大値のインデックス）
        class_probs = detection[5:]
        class_id = np.argmax(class_probs)
        class_conf = class_probs[class_id]
        
        # 総合信頼度
        total_conf = confidence * class_conf
        if total_conf < conf_threshold:
            continue
        
        # 座標変換（center format -> corner format）
        x1 = (x_center - width / 2) * scale_x
        y1 = (y_center - height / 2) * scale_y
        x2 = (x_center + width / 2) * scale_x
        y2 = (y_center + height / 2) * scale_y
        
        # 境界チェック
        x1 = max(0, min(orig_w, x1))
        y1 = max(0, min(orig_h, y1))
        x2 = max(0, min(orig_w, x2))
        y2 = max(0, min(orig_h, y2))
        
        # COCO クラス名（簡易版）
        coco_classes = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
            "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
            "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
            "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
            "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
            "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
            "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
            "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
            "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
            "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
            "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        ]
        
        class_name = coco_classes[class_id] if class_id < len(coco_classes) else f"class_{class_id}"
        
        detection_result = {
            "class": class_name,
            "confidence": float(total_conf),
            "bbox": {
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2)
            }
        }
        detections.append(detection_result)
    
    return detections

if __name__ == "__main__":
    main()
import os
import sys
import logging
import argparse
from minio import Minio
import torch
import cv2
from ultralytics import YOLO
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Detect objects in an image from MinIO using YOLO.")
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model to use")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--draw-boxes", type=bool, default=True, help="Draw bounding boxes on output")
    args = parser.parse_args()

    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    local_input = "/tmp/input_image"
    local_output = "/tmp/output_image"

    try:
        client = Minio(minio_endpoint, access_key=minio_access_key, secret_key=minio_secret_key, secure=False)
        logging.info(f"Downloading {args.input_path} from bucket {args.input_bucket}...")
        client.fget_object(args.input_bucket, args.input_path, local_input)

        # モデルのロード
        logging.info(f"Loading YOLO model: {args.model}")
        model = YOLO(args.model)
        
        # 画像の読み込みと推論
        logging.info("Running object detection...")
        results = model(local_input, conf=args.confidence)

        # 結果の処理
        img = cv2.imread(local_input)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())
                    
                    # 検出情報を記録
                    detection = {
                        "class": model.names[cls],
                        "confidence": float(conf),
                        "bbox": {
                            "x1": float(x1),
                            "y1": float(y1),
                            "x2": float(x2),
                            "y2": float(y2)
                        }
                    }
                    detections.append(detection)
                    
                    # バウンディングボックスを描画
                    if args.draw_boxes:
                        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        label = f"{model.names[cls]}: {conf:.2f}"
                        cv2.putText(img, label, (int(x1), int(y1) - 10), 
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

if __name__ == "__main__":
    main()
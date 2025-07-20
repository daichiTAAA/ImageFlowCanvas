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
    parser.add_argument("--resize-metadata", default=None, help="Path to resize metadata JSON for coordinate transformation")
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
        
        # リサイズメタデータの読み込み（座標変換用）
        resize_metadata = None
        if args.resize_metadata:
            try:
                metadata_path = "/tmp/resize_metadata.json"
                client.fget_object(args.input_bucket, args.resize_metadata, metadata_path)
                with open(metadata_path, 'r') as f:
                    resize_metadata = json.load(f)
                logging.info(f"Loaded resize metadata: {resize_metadata}")
            except Exception as e:
                logging.warning(f"Could not load resize metadata: {e}, proceeding without coordinate correction")

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
        
        # YOLOモデルの入力・出力名（config.pbtxtで定義済み）
        input_name = "images"
        output_name = "output0"
        
        logging.info(f"Using input: {input_name}, output: {output_name}")
        
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
            args.confidence,
            resize_metadata
        )
        
        # バウンディングボックスを描画
        if args.draw_boxes:
            for detection in detections:
                bbox = detection["bbox"]
                x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
                
                # ボックスの線を描画（線の太さ: 2）
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # ラベルテキストの設定
                label = f"{detection['class']}: {detection['confidence']:.2f}"
                
                # テキストサイズを取得してラベル背景を描画
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                font_thickness = 1  # テキストの太さを1に変更（読みやすく）
                
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
                
                # 半透明の背景を作成
                overlay = img.copy()
                cv2.rectangle(overlay, (x1, y1 - text_height - 10), (x1 + text_width, y1), (0, 0, 0), -1)
                
                # 半透明効果を適用（透明度0.6）
                alpha = 0.6
                cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
                
                # テキストを描画（白文字、太さ1）
                cv2.putText(img, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), font_thickness)

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
        
        # 検知結果JSONをMinIOに保存
        detection_json_filename = args.output_path.replace('.png', '_detections.json').replace('.jpg', '_detections.json')
        logging.info(f"Uploading detection results {detection_json_filename} to bucket {args.output_bucket}...")
        client.fput_object(args.output_bucket, detection_json_filename, "/tmp/result.json")
        logging.info("Detection results JSON upload complete.")
        
        print(json.dumps(result_data))

    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e)
        }
        logging.error(f"An error occurred: {e}")
        print(json.dumps(error_result))
        sys.exit(1)

def calculate_iou(box1, box2):
    """
    2つのバウンディングボックス間のIoU（Intersection over Union）を計算
    """
    x1 = max(box1["x1"], box2["x1"])
    y1 = max(box1["y1"], box2["y1"])
    x2 = min(box1["x2"], box2["x2"])
    y2 = min(box1["y2"], box2["y2"])
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    
    area1 = (box1["x2"] - box1["x1"]) * (box1["y2"] - box1["y1"])
    area2 = (box2["x2"] - box2["x1"]) * (box2["y2"] - box2["y1"])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0

def non_maximum_suppression(detections, iou_threshold=0.5):
    """
    Non-Maximum Suppressionを適用して重複する検出を除去
    """
    if not detections:
        return detections
    
    # 信頼度順にソート（降順）
    detections = sorted(detections, key=lambda x: x["confidence"], reverse=True)
    
    filtered_detections = []
    
    for current_detection in detections:
        # 現在の検出が既に選択された検出と重複しているかチェック
        should_keep = True
        
        for kept_detection in filtered_detections:
            # 同じクラスの場合のみNMSを適用
            if current_detection["class"] == kept_detection["class"]:
                iou = calculate_iou(current_detection["bbox"], kept_detection["bbox"])
                if iou > iou_threshold:
                    should_keep = False
                    break
        
        if should_keep:
            filtered_detections.append(current_detection)
    
    return filtered_detections

def post_process_yolo_output(output, orig_w, orig_h, input_w, input_h, conf_threshold, resize_metadata=None):
    """
    YOLO11の出力を後処理して検出結果を取得
    リサイズメタデータがある場合は、座標を元画像サイズに正しく変換する
    YOLO11 output format: [1, 84, 8400] -> [84, 8400] where 84 = [x, y, w, h, 80 class scores]
    """
    detections = []
    
    # YOLO11の実際の出力形式: [1, 84, 8400]
    if len(output.shape) == 3:
        output = output[0]  # バッチ次元を削除 -> [84, 8400]
    
    # 転置して [8400, 84] に変更（各行が1つの検出結果）
    if output.shape[0] == 84:
        output = output.T  # [8400, 84]
    
    logging.info(f"YOLO output shape after processing: {output.shape}")
    
    # 座標変換の設定
    if resize_metadata and "original_size" in resize_metadata and "scale_factors" in resize_metadata:
        # 座標変換チェーン: YOLO(640x640) -> リサイズ画像 -> 元画像
        true_orig_w = resize_metadata["original_size"]["width"]
        true_orig_h = resize_metadata["original_size"]["height"]
        resize_scale_x = 1.0 / resize_metadata["scale_factors"]["x"]  # リサイズ画像から元画像への逆変換
        resize_scale_y = 1.0 / resize_metadata["scale_factors"]["y"]
        
        # YOLOからリサイズ画像への変換
        yolo_to_resized_scale_x = orig_w / input_w
        yolo_to_resized_scale_y = orig_h / input_h
        
        # 最終的な変換係数（YOLO -> 元画像）
        final_scale_x = yolo_to_resized_scale_x * resize_scale_x
        final_scale_y = yolo_to_resized_scale_y * resize_scale_y
        
        # 最終出力サイズ
        final_w = true_orig_w
        final_h = true_orig_h
        
        logging.info(f"Using coordinate transformation chain: YOLO({input_w}x{input_h}) -> Resized({orig_w}x{orig_h}) -> Original({true_orig_w}x{true_orig_h})")
        logging.info(f"Scale factors: x={final_scale_x:.4f}, y={final_scale_y:.4f}")
    else:
        # 従来の方法（リサイズメタデータがない場合）
        final_scale_x = orig_w / input_w
        final_scale_y = orig_h / input_h
        final_w = orig_w
        final_h = orig_h
        logging.info(f"Using direct transformation: YOLO({input_w}x{input_h}) -> Current({orig_w}x{orig_h})")
        logging.info(f"Scale factors: x={final_scale_x:.4f}, y={final_scale_y:.4f}")
    
    # COCO クラス名（YOLO11で使用される80クラス）
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
    
    for detection in output:
        if len(detection) < 84:
            continue
            
        # YOLO11 形式: [x_center, y_center, width, height, class_prob_0, class_prob_1, ..., class_prob_79]
        x_center, y_center, width, height = detection[:4]
        class_probs = detection[4:84]  # 80個のクラス確率
        
        # 最大確率のクラスを取得
        class_id = np.argmax(class_probs)
        confidence = class_probs[class_id]
        
        # 信頼度チェック
        if confidence < conf_threshold:
            continue
        
        # 座標変換（center format -> corner format）
        x1 = (x_center - width / 2) * final_scale_x
        y1 = (y_center - height / 2) * final_scale_y
        x2 = (x_center + width / 2) * final_scale_x
        y2 = (y_center + height / 2) * final_scale_y
        
        # 境界チェック
        x1 = max(0, min(final_w, x1))
        y1 = max(0, min(final_h, y1))
        x2 = max(0, min(final_w, x2))
        y2 = max(0, min(final_h, y2))
        
        # ボックスのサイズチェック（あまりに小さいものは除外）
        if (x2 - x1) < 1 or (y2 - y1) < 1:
            continue
        
        class_name = coco_classes[class_id] if class_id < len(coco_classes) else f"class_{class_id}"
        
        detection_result = {
            "class": class_name,
            "confidence": float(confidence),
            "bbox": {
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2)
            }
        }
        detections.append(detection_result)
    
    # Non-Maximum Suppressionを適用して重複検出を除去
    detections = non_maximum_suppression(detections, iou_threshold=0.4)
    
    logging.info(f"After NMS: {len(detections)} detections remaining")
    
    return detections

if __name__ == "__main__":
    main()
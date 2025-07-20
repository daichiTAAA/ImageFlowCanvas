import os
import sys
import logging
import argparse
from minio import Minio
import cv2
import json

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # 引数パーサーの設定
    parser = argparse.ArgumentParser(description="Resize an image from MinIO.")
    parser.add_argument("--input-bucket", required=True, help="MinIO bucket for input image")
    parser.add_argument("--input-path", required=True, help="Path to the input image in the bucket")
    parser.add_argument("--output-bucket", required=True, help="MinIO bucket for output image")
    parser.add_argument("--output-path", required=True, help="Path for the output image in the bucket")
    parser.add_argument("--width", type=int, default=800, help="Target width")
    parser.add_argument("--height", type=int, default=600, help="Target height")
    parser.add_argument("--maintain-aspect", type=bool, default=True, help="Maintain aspect ratio")
    args = parser.parse_args()

    # MinIO接続情報 (環境変数から取得)
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    # ローカルの一時ファイルパス
    local_input = "/tmp/input_image"
    local_output = "/tmp/output_image"

    try:
        # MinIOクライアントの初期化
        client = Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=False
        )
        logging.info(f"Successfully connected to MinIO at {minio_endpoint}")

        # 1. MinIOから画像をダウンロード
        logging.info(f"Downloading {args.input_path} from bucket {args.input_bucket}...")
        client.fget_object(args.input_bucket, args.input_path, local_input)
        logging.info(f"Downloaded to {local_input}")

        # 2. 画像のリサイズ処理 (OpenCVを使用)
        image = cv2.imread(local_input)
        if image is None:
            raise ValueError("Could not read the input image.")
        
        original_height, original_width = image.shape[:2]
        logging.info(f"Original image size: {original_width}x{original_height}")
        
        # アスペクト比を維持する場合の計算
        if args.maintain_aspect:
            aspect_ratio = original_width / original_height
            if args.width / args.height > aspect_ratio:
                # 高さに合わせて幅を調整
                new_width = int(args.height * aspect_ratio)
                new_height = args.height
            else:
                # 幅に合わせて高さを調整
                new_width = args.width
                new_height = int(args.width / aspect_ratio)
        else:
            new_width = args.width
            new_height = args.height

        resized_image = cv2.resize(image, (new_width, new_height))
        logging.info(f"Resized image to {new_width}x{new_height}")
        
        # 元のファイル形式を維持するために拡張子を取得
        _, ext = os.path.splitext(args.output_path)
        if not ext:
            ext = ".jpg"  # デフォルト拡張子
        
        output_file = local_output + ext
        cv2.imwrite(output_file, resized_image)
        logging.info(f"Saved resized image to {output_file}")

        # 3. 処理結果をMinIOにアップロード
        if not client.bucket_exists(args.output_bucket):
            logging.warning(f"Output bucket '{args.output_bucket}' not found. Creating it.")
            client.make_bucket(args.output_bucket)

        logging.info(f"Uploading {args.output_path} to bucket {args.output_bucket}...")
        client.fput_object(args.output_bucket, args.output_path, output_file)
        logging.info("Upload complete.")

        # 4. 結果をJSON形式で出力（Argo Workflowsで使用）
        scale_x = new_width / original_width
        scale_y = new_height / original_height
        
        result = {
            "status": "success",
            "input_file": f"{args.input_bucket}/{args.input_path}",
            "output_file": f"{args.output_bucket}/{args.output_path}",
            "original_size": {"width": original_width, "height": original_height},
            "new_size": {"width": new_width, "height": new_height},
            "scale_factors": {"x": scale_x, "y": scale_y}
        }
        
        # 結果をファイルに保存（Argo Workflowsのアーティファクトとして使用）
        with open("/tmp/result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # メタデータをMinIOに保存（次のステップで使用）
        metadata_filename = args.output_path.replace('.png', '_metadata.json').replace('.jpg', '_metadata.json')
        with open("/tmp/metadata.json", "w") as f:
            json.dump(result, f, indent=2)
        
        logging.info(f"Uploading metadata {metadata_filename} to bucket {args.output_bucket}...")
        client.fput_object(args.output_bucket, metadata_filename, "/tmp/metadata.json")
        logging.info("Metadata upload complete.")
        
        print(json.dumps(result))  # 標準出力にも出力

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
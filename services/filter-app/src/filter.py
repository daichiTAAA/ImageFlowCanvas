import os
import sys
import logging
import argparse
from minio import Minio
import cv2
import numpy as np
from skimage import filters
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def apply_filter(image, filter_type, intensity=1.0):
    """画像にフィルタを適用する"""
    if filter_type == "blur":
        kernel_size = int(5 * intensity)
        if kernel_size % 2 == 0:
            kernel_size += 1
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    elif filter_type == "sharpen":
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]]) * intensity
        return cv2.filter2D(image, -1, kernel)
    
    elif filter_type == "edge":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    elif filter_type == "emboss":
        kernel = np.array([[-2, -1, 0],
                          [-1,  1, 1],
                          [ 0,  1, 2]]) * intensity
        return cv2.filter2D(image, -1, kernel)
    
    else:
        logging.warning(f"Unknown filter type: {filter_type}. Returning original image.")
        return image

def main():
    parser = argparse.ArgumentParser(description="Apply filters to an image from MinIO.")
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--filter-type", default="blur", 
                       choices=["blur", "sharpen", "edge", "emboss"],
                       help="Type of filter to apply")
    parser.add_argument("--intensity", type=float, default=1.0, 
                       help="Filter intensity (0.0 - 5.0)")
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

        # 画像の読み込み
        image = cv2.imread(local_input)
        if image is None:
            raise ValueError("Could not read the input image.")

        original_height, original_width = image.shape[:2]
        logging.info(f"Loaded image: {original_width}x{original_height}")

        # フィルタを適用
        logging.info(f"Applying {args.filter_type} filter with intensity {args.intensity}")
        filtered_image = apply_filter(image, args.filter_type, args.intensity)

        # 結果を保存
        _, ext = os.path.splitext(args.output_path)
        if not ext:
            ext = ".jpg"
        
        output_file = local_output + ext
        cv2.imwrite(output_file, filtered_image)
        logging.info(f"Filter applied. Result saved to {output_file}")

        # MinIOにアップロード
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
            "filter_applied": args.filter_type,
            "intensity": args.intensity,
            "image_size": {"width": original_width, "height": original_height}
        }
        
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
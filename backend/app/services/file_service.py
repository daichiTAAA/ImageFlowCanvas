import time
import asyncio
from fastapi import UploadFile
import os
import uuid
from typing import Tuple, List, Dict
import aiofiles
from io import BytesIO
import json
from datetime import datetime

# Optional MinIO import for cases where MinIO is not available
try:
    from minio import Minio
    from minio.error import S3Error

    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    print("Warning: MinIO is not available. File service will run in mock mode.")


class FileService:
    def __init__(self):
        self.minio_available = MINIO_AVAILABLE
        self.bucket_name = "imageflow-files"
        self.mock_storage = {}  # For mock mode
        self.max_retries = 3
        self.retry_delay = 1  # seconds

        print(f"FileService: MINIO_AVAILABLE = {MINIO_AVAILABLE}")

        if self.minio_available:
            self._initialize_minio_with_retry()
        else:
            self.minio_client = None

        if not self.minio_available:
            print("FileService: Running in mock mode")

    def _initialize_minio_with_retry(self):
        """MinIOの初期化をリトライ付きで実行"""
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio-service:9000")

        for attempt in range(self.max_retries):
            try:
                print(
                    f"FileService: Attempting to connect to MinIO at {minio_endpoint} (attempt {attempt + 1}/{self.max_retries})"
                )

                self.minio_client = Minio(
                    endpoint=minio_endpoint,
                    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    secure=False,
                )

                # 接続テスト - バケット一覧を取得してみる
                buckets = list(self.minio_client.list_buckets())
                print(
                    f"FileService: MinIO connection test successful. Found {len(buckets)} buckets"
                )

                # バケットの確保を試行
                success = self._ensure_bucket_exists_with_retry()
                if success:
                    print(
                        f"FileService: MinIO connection successful, bucket '{self.bucket_name}' ready"
                    )
                    print(f"FileService: Running in MinIO mode")
                    return
                else:
                    print(
                        f"FileService: Bucket creation failed on attempt {attempt + 1}"
                    )

            except Exception as e:
                print(
                    f"FileService: MinIO connection attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    print(f"FileService: Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    print(
                        f"FileService: All {self.max_retries} connection attempts failed, falling back to mock mode"
                    )
                    self.minio_available = False

    def _ensure_bucket_exists_with_retry(self) -> bool:
        """バケット作成をリトライ付きで実行"""
        if not self.minio_available:
            return False

        for attempt in range(self.max_retries):
            try:
                # バケット存在確認
                bucket_exists = self.minio_client.bucket_exists(self.bucket_name)
                print(
                    f"FileService: Bucket '{self.bucket_name}' exists: {bucket_exists}"
                )

                if not bucket_exists:
                    print(f"FileService: Creating bucket '{self.bucket_name}'...")
                    self.minio_client.make_bucket(self.bucket_name)
                    print(
                        f"FileService: Bucket '{self.bucket_name}' created successfully"
                    )

                # 作成後の確認
                if self.minio_client.bucket_exists(self.bucket_name):
                    print(f"FileService: Bucket '{self.bucket_name}' is ready")
                    return True
                else:
                    print(
                        f"FileService: Bucket verification failed on attempt {attempt + 1}"
                    )

            except Exception as e:
                print(
                    f"FileService: Bucket operation attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(1)

        return False

    def _ensure_bucket_exists(self):
        """バケットが存在することを確認し、なければ作成（レガシーメソッド）"""
        return self._ensure_bucket_exists_with_retry()

    async def upload_file(self, file: UploadFile, file_id: str = None) -> str:
        """ファイルをMinIOにアップロード"""
        if file_id is None:
            file_id = str(uuid.uuid4())

        file_extension = ""
        if file.filename:
            file_extension = os.path.splitext(file.filename)[1]

        object_name = f"{file_id}{file_extension}"

        # ファイルの内容を読み取り
        content = await file.read()

        if not self.minio_available:
            # Mock mode - store in memory
            self.mock_storage[file_id] = {
                "content": content,
                "filename": file.filename or object_name,
                "content_type": file.content_type or "application/octet-stream",
            }
            print(f"Mock file upload: {file_id} ({file.filename})")
            return file_id

        try:
            self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=BytesIO(content),
                length=len(content),
                content_type=file.content_type,
            )
            # Return the actual MinIO object name instead of just file_id
            return object_name
        except Exception as e:
            raise Exception(f"Failed to upload file: {e}")

    async def download_file(self, file_id: str) -> Tuple[BytesIO, str, str]:
        """ファイルをMinIOからダウンロード"""
        if not self.minio_available:
            # Mock mode
            if file_id not in self.mock_storage:
                raise FileNotFoundError(f"File with ID {file_id} not found")

            mock_file = self.mock_storage[file_id]
            return (
                BytesIO(mock_file["content"]),
                mock_file["filename"],
                mock_file["content_type"],
            )

        try:
            # オブジェクトのメタデータを取得してファイル拡張子を特定
            objects = self.minio_client.list_objects(self.bucket_name, prefix=file_id)
            object_name = None
            for obj in objects:
                if obj.object_name.startswith(file_id):
                    object_name = obj.object_name
                    break

            if not object_name:
                raise FileNotFoundError(f"File with ID {file_id} not found")

            response = self.minio_client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            # ファイル名とコンテンツタイプを推定
            filename = object_name
            content_type = "application/octet-stream"

            if object_name.lower().endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            elif object_name.lower().endswith(".png"):
                content_type = "image/png"
            elif object_name.lower().endswith(".tiff"):
                content_type = "image/tiff"

            return BytesIO(data), filename, content_type

        except Exception as e:
            if hasattr(e, "code") and e.code == "NoSuchKey":
                raise FileNotFoundError(f"File with ID {file_id} not found")
            else:
                raise Exception(f"Failed to download file: {e}")

    async def delete_file(self, file_id: str) -> bool:
        """ファイルをMinIOから削除"""
        if not self.minio_available:
            # Mock mode
            if file_id in self.mock_storage:
                del self.mock_storage[file_id]
                print(f"Mock file deleted: {file_id}")
                return True
            return False

        try:
            # オブジェクト名を特定
            objects = self.minio_client.list_objects(self.bucket_name, prefix=file_id)
            object_name = None
            for obj in objects:
                if obj.object_name.startswith(file_id):
                    object_name = obj.object_name
                    break

            if not object_name:
                return False

            self.minio_client.remove_object(self.bucket_name, object_name)
            return True

        except Exception as e:
            if hasattr(e, "code") and e.code == "NoSuchKey":
                return False
            else:
                raise Exception(f"Failed to delete file: {e}")

    async def get_file_info(self, file_path: str) -> dict:
        """ファイル情報を取得（サイズ、コンテンツタイプなど）"""
        if not self.minio_available:
            # Mock mode
            # file_pathからfile_idを抽出（最後のパスセグメント）
            file_id = os.path.basename(file_path)
            if file_id in self.mock_storage:
                mock_file = self.mock_storage[file_id]
                return {
                    "size": len(mock_file["content"]),
                    "content_type": mock_file["content_type"],
                    "filename": mock_file["filename"],
                }
            return None

        try:
            # file_pathからobject_nameを抽出
            object_name = file_path
            if file_path.startswith("/"):
                object_name = file_path[1:]  # 先頭のスラッシュを除去

            # MinIOからオブジェクト情報を取得
            stat = self.minio_client.stat_object(self.bucket_name, object_name)

            return {
                "size": stat.size,
                "content_type": stat.content_type or "application/octet-stream",
                "filename": os.path.basename(object_name),
                "etag": stat.etag,
                "last_modified": stat.last_modified,
            }

        except Exception as e:
            if hasattr(e, "code") and e.code == "NoSuchKey":
                return None
            else:
                print(f"Failed to get file info for {file_path}: {e}")
                return None

    async def list_files(
        self, prefix: str = "", file_extension: str = None
    ) -> List[Dict]:
        """ファイル一覧を取得"""
        if not self.minio_available:
            # Mock mode
            files = []
            for file_id, file_data in self.mock_storage.items():
                filename = file_data["filename"]
                if prefix and not filename.startswith(prefix):
                    continue
                if file_extension and not filename.endswith(file_extension):
                    continue

                files.append(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "content_type": file_data["content_type"],
                        "size": len(file_data["content"]),
                        "last_modified": datetime.now().isoformat(),
                    }
                )
            return files

        try:
            objects = self.minio_client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )

            files = []
            for obj in objects:
                # Filter by file extension if specified
                if file_extension and not obj.object_name.endswith(file_extension):
                    continue

                files.append(
                    {
                        "file_id": obj.object_name,
                        "filename": os.path.basename(obj.object_name),
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": (
                            obj.last_modified.isoformat() if obj.last_modified else None
                        ),
                        "etag": obj.etag,
                        "content_type": self._get_content_type_from_extension(
                            obj.object_name
                        ),
                    }
                )

            return files
        except Exception as e:
            print(f"Failed to list files: {e}")
            return []

    async def get_json_content(self, file_path: str) -> Dict:
        """JSONファイルの内容を取得"""
        if not self.minio_available:
            # Mock mode
            file_id = os.path.basename(file_path)
            if file_id in self.mock_storage:
                try:
                    content = self.mock_storage[file_id]["content"].decode("utf-8")
                    return json.loads(content)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON content")
            raise FileNotFoundError("File not found")

        try:
            object_name = file_path
            if file_path.startswith("/"):
                object_name = file_path[1:]

            response = self.minio_client.get_object(self.bucket_name, object_name)
            content = response.read().decode("utf-8")
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON content")
        except Exception as e:
            if hasattr(e, "code") and e.code == "NoSuchKey":
                raise FileNotFoundError("File not found")
            raise Exception(f"Failed to get JSON content: {e}")

    def _get_content_type_from_extension(self, filename: str) -> str:
        """ファイル拡張子からコンテンツタイプを推定"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".json": "application/json",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".xml": "application/xml",
            ".pdf": "application/pdf",
        }
        return content_types.get(ext, "application/octet-stream")

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
import os
import uuid
from typing import Tuple
import aiofiles
from io import BytesIO

class FileService:
    def __init__(self):
        self.minio_client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=False
        )
        self.bucket_name = "imageflow-files"
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """バケットが存在することを確認し、なければ作成"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error creating bucket: {e}")
    
    async def upload_file(self, file: UploadFile) -> str:
        """ファイルをMinIOにアップロード"""
        file_id = str(uuid.uuid4())
        file_extension = ""
        if file.filename:
            file_extension = os.path.splitext(file.filename)[1]
        
        object_name = f"{file_id}{file_extension}"
        
        # ファイルの内容を読み取り
        content = await file.read()
        
        try:
            self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=BytesIO(content),
                length=len(content),
                content_type=file.content_type
            )
            return file_id
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")
    
    async def download_file(self, file_id: str) -> Tuple[BytesIO, str, str]:
        """ファイルをMinIOからダウンロード"""
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
            
            if object_name.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif object_name.lower().endswith('.png'):
                content_type = "image/png"
            elif object_name.lower().endswith('.tiff'):
                content_type = "image/tiff"
            
            return BytesIO(data), filename, content_type
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File with ID {file_id} not found")
            else:
                raise Exception(f"Failed to download file: {e}")
    
    async def delete_file(self, file_id: str) -> bool:
        """ファイルをMinIOから削除"""
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
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            else:
                raise Exception(f"Failed to delete file: {e}")
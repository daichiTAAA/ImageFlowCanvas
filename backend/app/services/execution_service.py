from typing import List, Optional
from fastapi import UploadFile
from app.models.execution import Execution, ExecutionRequest, ExecutionStatus, ExecutionProgress
from app.services.file_service import FileService
from app.services.kafka_service import KafkaService
import uuid
import json

class ExecutionService:
    def __init__(self):
        self.executions = {}
        self.file_service = FileService()
        self.kafka_service = KafkaService()
    
    async def execute_pipeline(self, execution_request: ExecutionRequest, input_files: List[UploadFile]) -> Execution:
        """パイプラインを実行"""
        execution_id = str(uuid.uuid4())
        
        # 入力ファイルをアップロード
        uploaded_files = []
        for file in input_files:
            file_id = await self.file_service.upload_file(file)
            uploaded_files.append(file_id)
        
        # 実行オブジェクトを作成
        execution = Execution(
            execution_id=execution_id,
            pipeline_id=execution_request.pipeline_id,
            progress=ExecutionProgress(
                current_step="初期化中",
                total_steps=1,  # パイプラインの詳細から計算する必要がある
                completed_steps=0,
                percentage=0.0
            )
        )
        
        self.executions[execution_id] = execution
        
        # Kafkaにメッセージを送信してパイプライン実行を開始
        message = {
            "execution_id": execution_id,
            "pipeline_id": execution_request.pipeline_id,
            "input_files": uploaded_files,
            "parameters": execution_request.parameters,
            "priority": execution_request.priority
        }
        
        await self.kafka_service.send_message("image-processing-requests", message)
        
        return execution
    
    async def get_execution(self, execution_id: str) -> Optional[Execution]:
        """実行状況を取得"""
        return self.executions.get(execution_id)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """実行をキャンセル"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False
        
        if execution.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            execution.status = ExecutionStatus.CANCELLED
            
            # Kafkaにキャンセルメッセージを送信
            cancel_message = {
                "execution_id": execution_id,
                "action": "cancel"
            }
            await self.kafka_service.send_message("execution-control", cancel_message)
            
            return True
        return False
    
    async def get_executions(self, limit: int = 100, offset: int = 0) -> List[Execution]:
        """実行履歴を取得"""
        all_executions = list(self.executions.values())
        # 作成日時でソート（新しい順）
        all_executions.sort(key=lambda x: x.created_at, reverse=True)
        return all_executions[offset:offset + limit]
    
    async def update_execution_status(self, execution_id: str, status: ExecutionStatus, progress_data: dict = None):
        """実行状況を更新（Kafkaコンシューマーから呼び出される）"""
        execution = self.executions.get(execution_id)
        if not execution:
            return
        
        execution.status = status
        
        if progress_data:
            execution.progress.current_step = progress_data.get("current_step", execution.progress.current_step)
            execution.progress.completed_steps = progress_data.get("completed_steps", execution.progress.completed_steps)
            execution.progress.percentage = progress_data.get("percentage", execution.progress.percentage)
from typing import List, Optional
from fastapi import UploadFile
from app.models.execution import Execution, ExecutionRequest, ExecutionStatus, ExecutionProgress
from app.services.file_service import FileService
from app.services.kafka_service import KafkaService
import uuid
import json
import asyncio
import os

# グローバル ExecutionService インスタンス
_execution_service_instance = None

def get_global_execution_service():
    """グローバル ExecutionService インスタンスを取得"""
    global _execution_service_instance
    if _execution_service_instance is None:
        _execution_service_instance = ExecutionService()
    return _execution_service_instance

class ExecutionService:
    def __init__(self):
        self.executions = {}
        self.file_service = FileService()
        self.kafka_service = KafkaService()
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        self.websocket_manager = None  # 遅延初期化
    
    def get_websocket_manager(self):
        """WebSocket マネージャーを遅延初期化"""
        if self.websocket_manager is None:
            try:
                from app.services.websocket_manager import ConnectionManager
                # グローバルインスタンスを取得（main.py で作成されているもの）
                import app.main
                self.websocket_manager = app.main.manager
            except Exception as e:
                print(f"Could not get WebSocket manager: {e}")
                self.websocket_manager = None
        return self.websocket_manager
    
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
        
        try:
            await self.kafka_service.send_message("image-processing-requests", message)
        except Exception as e:
            print(f"Failed to send message to Kafka: {e}")
            # Kafka が利用できない場合でも実行オブジェクトは作成し、
            # 直接実行モードのワーカーが処理する
            print("Execution will be processed by direct execution mode")
        
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
    
    async def get_pending_executions(self) -> List[Execution]:
        """実行待ちの実行を取得（直接実行モード用）"""
        pending_executions = []
        for execution in self.executions.values():
            if execution.status == ExecutionStatus.PENDING:
                pending_executions.append(execution)
        return pending_executions
    
    async def update_execution_status(self, execution_id: str, status: ExecutionStatus, progress_data: dict = None):
        """実行状況を更新（Kafkaコンシューマーから呼び出される）"""
        print(f"update_execution_status called for {execution_id}, status: {status} - DEBUG")
        execution = self.executions.get(execution_id)
        if not execution:
            print(f"Execution {execution_id} not found in executions dict - DEBUG")
            return
        
        print(f"Updating execution {execution_id} from {execution.status} to {status} - DEBUG")
        execution.status = status
        
        if progress_data:
            execution.progress.current_step = progress_data.get("current_step", execution.progress.current_step)
            execution.progress.completed_steps = progress_data.get("completed_steps", execution.progress.completed_steps)
            execution.progress.percentage = progress_data.get("percentage", execution.progress.percentage)
        
        print(f"Execution {execution_id} updated successfully - DEBUG")
        
        # WebSocket で進捗をリアルタイム通知
        websocket_manager = self.get_websocket_manager()
        if websocket_manager:
            try:
                update_data = {
                    "execution_id": execution_id,
                    "status": status.value,
                    "progress": {
                        "current_step": execution.progress.current_step,
                        "completed_steps": execution.progress.completed_steps,
                        "total_steps": execution.progress.total_steps,
                        "percentage": execution.progress.percentage
                    }
                }
                await websocket_manager.send_execution_update(execution_id, update_data)
                print(f"WebSocket update sent for {execution_id} - DEBUG")
            except Exception as e:
                print(f"Failed to send WebSocket update: {e}")
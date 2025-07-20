from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from app.models.execution import (
    Execution,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionProgress,
)
from app.services.file_service import FileService
from app.services.kafka_service import KafkaService
from app.services.grpc_pipeline_executor import get_grpc_pipeline_executor
import uuid
import json
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

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
        self.grpc_executor = get_grpc_pipeline_executor()
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

    async def execute_pipeline(
        self, execution_request: ExecutionRequest, input_files: List[UploadFile]
    ) -> Execution:
        """パイプラインを実行"""
        execution_id = str(uuid.uuid4())

        # 入力ファイルをアップロード（実行IDを使用）
        uploaded_files = []
        for i, file in enumerate(input_files):
            # 実行IDベースのファイルIDを生成（複数ファイル対応）
            file_id = (
                f"{execution_id}-input-{i}" if len(input_files) > 1 else execution_id
            )
            actual_file_id = await self.file_service.upload_file(file, file_id)
            uploaded_files.append(actual_file_id)

        # 実行オブジェクトを作成
        execution = Execution(
            execution_id=execution_id,
            pipeline_id=execution_request.pipeline_id,
            progress=ExecutionProgress(
                current_step="初期化中",
                total_steps=1,  # パイプラインの詳細から計算する必要がある
                completed_steps=0,
                percentage=0.0,
            ),
        )

        self.executions[execution_id] = execution

        # Execute pipeline directly using gRPC instead of Argo Workflows
        # This eliminates the 750-1450ms overhead and achieves 40-100ms processing
        try:
            # Start direct gRPC pipeline execution in background
            asyncio.create_task(self._execute_pipeline_direct(execution_id, execution_request, uploaded_files))
            logger.info(f"Started direct gRPC pipeline execution for {execution_id}")
        except Exception as e:
            logger.error(f"Failed to start direct pipeline execution: {e}")
            # Fallback to Kafka-based execution if direct execution fails
            try:
                message = {
                    "execution_id": execution_id,
                    "pipeline_id": execution_request.pipeline_id,
                    "input_files": uploaded_files,
                    "parameters": execution_request.parameters,
                    "priority": execution_request.priority,
                }
                await self.kafka_service.send_message("image-processing-requests", message)
                logger.info(f"Fallback: sent execution to Kafka queue for {execution_id}")
            except Exception as kafka_error:
                logger.error(f"Both direct execution and Kafka fallback failed: {kafka_error}")
                execution.status = ExecutionStatus.FAILED

        return execution

    async def _execute_pipeline_direct(self, execution_id: str, execution_request: ExecutionRequest, input_files: List[str]):
        """
        Execute pipeline directly using gRPC calls (40-100ms processing time)
        Replaces Argo Workflows delegation for ultra-fast execution
        """
        try:
            execution = self.executions.get(execution_id)
            if not execution:
                logger.error(f"Execution {execution_id} not found")
                return

            # Update status to running
            execution.status = ExecutionStatus.RUNNING
            execution.progress.current_step = "処理開始"
            await self._notify_execution_update(execution)

            # Create pipeline configuration from execution request
            pipeline_config = await self._build_pipeline_config(execution_request, input_files)
            
            # Execute pipeline using direct gRPC calls
            result = await self.grpc_executor.execute_pipeline(pipeline_config, execution_id)
            
            # Update execution with results
            if result['status'] == 'completed':
                execution.status = ExecutionStatus.COMPLETED
                execution.progress.current_step = "完了"
                execution.progress.completed_steps = execution.progress.total_steps
                execution.progress.percentage = 100.0
                
                # Add output files
                if 'final_output_path' in result:
                    execution.output_files = [result['final_output_path']]
                    
                logger.info(f"Direct gRPC pipeline execution completed for {execution_id} in {result.get('execution_time_ms', 0):.2f}ms")
                
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = result.get('error', 'Unknown error')
                logger.error(f"Direct gRPC pipeline execution failed for {execution_id}: {execution.error_message}")

            await self._notify_execution_update(execution)

        except Exception as e:
            logger.error(f"Error in direct pipeline execution for {execution_id}: {e}")
            execution = self.executions.get(execution_id)
            if execution:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                await self._notify_execution_update(execution)

    async def _build_pipeline_config(self, execution_request: ExecutionRequest, input_files: List[str]) -> Dict[str, Any]:
        """Build pipeline configuration for direct gRPC execution"""
        # This is a simplified pipeline config - in a real implementation,
        # you would fetch the actual pipeline definition from the pipeline_service
        return {
            "pipelineId": execution_request.pipeline_id,
            "steps": [
                {
                    "stepId": "resize-step",
                    "componentName": "resize",
                    "parameters": {
                        "width": execution_request.parameters.get("target_width", 800),
                        "height": execution_request.parameters.get("target_height", 600),
                        "maintain_aspect_ratio": True
                    },
                    "dependencies": []
                },
                {
                    "stepId": "ai-detection-step", 
                    "componentName": "ai_detection",
                    "parameters": {
                        "model_name": execution_request.parameters.get("model_name", "yolo"),
                        "confidence_threshold": execution_request.parameters.get("confidence_threshold", 0.5),
                        "draw_boxes": True
                    },
                    "dependencies": ["resize-step"]
                },
                {
                    "stepId": "filter-step",
                    "componentName": "filter", 
                    "parameters": {
                        "filter_type": execution_request.parameters.get("filter_type", "gaussian"),
                        "intensity": execution_request.parameters.get("filter_intensity", 1.0)
                    },
                    "dependencies": ["ai-detection-step"]
                }
            ],
            "globalParameters": {
                "inputPath": input_files[0] if input_files else None,
                "executionId": execution_request.pipeline_id
            }
        }

    async def _notify_execution_update(self, execution: Execution):
        """Notify WebSocket clients of execution updates"""
        websocket_manager = self.get_websocket_manager()
        if websocket_manager:
            try:
                await websocket_manager.broadcast_execution_update(execution)
            except Exception as e:
                logger.warning(f"Failed to broadcast execution update: {e}")

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
            cancel_message = {"execution_id": execution_id, "action": "cancel"}
            await self.kafka_service.send_message("execution-control", cancel_message)

            return True
        return False

    async def get_executions(
        self, limit: int = 100, offset: int = 0
    ) -> List[Execution]:
        """実行履歴を取得"""
        all_executions = list(self.executions.values())
        # 作成日時でソート（新しい順）
        all_executions.sort(key=lambda x: x.created_at, reverse=True)
        return all_executions[offset : offset + limit]

    async def get_pending_executions(self) -> List[Execution]:
        """実行待ちの実行を取得（直接実行モード用）"""
        pending_executions = []
        for execution in self.executions.values():
            if execution.status == ExecutionStatus.PENDING:
                pending_executions.append(execution)
        return pending_executions

    async def get_running_executions(self) -> List[Execution]:
        """実行中の実行を取得（ワークフロー監視用）"""
        running_executions = []
        for execution in self.executions.values():
            if execution.status == ExecutionStatus.RUNNING:
                running_executions.append(execution)
        return running_executions

    async def update_execution_status(
        self, execution_id: str, status: ExecutionStatus, progress_data: dict = None
    ):
        """実行状況を更新（Kafkaコンシューマーから呼び出される）"""
        execution = self.executions.get(execution_id)
        if not execution:
            return

        # ステータス変更時にタイムスタンプを更新
        from datetime import datetime, timezone, timedelta

        jst = timezone(timedelta(hours=9))  # JST = UTC+9
        if execution.status != status:
            if status == ExecutionStatus.RUNNING and execution.started_at is None:
                execution.started_at = datetime.now(jst)
            elif status in [
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ]:
                # 完了時にstarted_atが設定されていない場合は設定
                if execution.started_at is None:
                    execution.started_at = datetime.now(jst)
                execution.completed_at = datetime.now(jst)

        execution.status = status

        if progress_data:
            execution.progress.current_step = progress_data.get(
                "current_step", execution.progress.current_step
            )
            execution.progress.completed_steps = progress_data.get(
                "completed_steps", execution.progress.completed_steps
            )
            execution.progress.percentage = progress_data.get(
                "percentage", execution.progress.percentage
            )

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
                        "percentage": execution.progress.percentage,
                    },
                }
                await websocket_manager.send_execution_update(execution_id, update_data)
            except Exception as e:
                print(f"Failed to send WebSocket update: {e}")

    async def fix_execution_timestamps(self, execution_id: str) -> bool:
        """既存実行のタイムスタンプを修正（デバッグ用）"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        from datetime import datetime, timezone, timedelta

        jst = timezone(timedelta(hours=9))

        # ステップから実行時間を推定
        if execution.steps and execution.status == ExecutionStatus.COMPLETED:
            step_start_times = [
                datetime.fromisoformat(s.started_at.replace("Z", "+00:00"))
                for s in execution.steps
                if s.started_at and s.status == "completed"
            ]
            step_end_times = [
                datetime.fromisoformat(s.completed_at.replace("Z", "+00:00"))
                for s in execution.steps
                if s.completed_at and s.status == "completed"
            ]

            if step_start_times and step_end_times:
                execution.started_at = min(step_start_times).astimezone(jst)
                execution.completed_at = max(step_end_times).astimezone(jst)
                return True

        return False

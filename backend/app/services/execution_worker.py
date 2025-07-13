import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any
from app.services.kafka_service import KafkaService
from app.services.component_service import ComponentService
from app.models.execution import ExecutionStatus, ExecutionStep, StepStatus
import logging

logger = logging.getLogger(__name__)

class ExecutionWorker:
    def __init__(self):
        self.kafka_service = KafkaService()
        self.component_service = ComponentService()
        self.execution_service = None  # 遅延初期化
        self.running = False
        
    def get_execution_service(self):
        """ExecutionServiceを遅延初期化"""
        from app.services.execution_service import get_global_execution_service
        return get_global_execution_service()
    
    async def start(self):
        """ワーカーを開始"""
        self.running = True
        logger.info("Execution worker started")
        
        # 常に直接実行モードで開始（Kafkaの問題を回避）
        logger.info("Starting direct execution mode")
        
        try:
            await self.start_direct_execution_mode()
        except Exception as e:
            logger.error(f"Error starting direct execution mode: {e}")
    
    async def stop(self):
        """ワーカーを停止"""
        self.running = False
        logger.info("Execution worker stopped")
    
    async def start_direct_execution_mode(self):
        """直接実行モード（Kafkaが利用できない場合）"""
        logger.info("Starting direct execution mode")
        execution_service = self.get_execution_service()
        
        # 実行待ちのタスクを定期的にチェック
        while self.running:
            try:
                # 実行待ちのタスクがあるかチェック
                pending_executions = await execution_service.get_pending_executions()
                
                if pending_executions:
                    logger.info(f"Found {len(pending_executions)} pending executions")
                
                for execution in pending_executions:
                    logger.info(f"Processing execution {execution.execution_id} in direct mode")
                    await self.process_execution_direct(execution)
                
                # 5秒間隔でチェック
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in direct execution mode: {e}")
                await asyncio.sleep(10)  # エラー時は長めに待機
    
    async def process_execution_direct(self, execution):
        """直接実行モードでの実行処理"""
        try:
            execution_service = self.get_execution_service()
            
            # 実行データを準備
            execution_data = {
                "execution_id": execution.execution_id,
                "pipeline_id": execution.pipeline_id,
                "input_files": [],  # 直接実行モードでは簡略化
                "parameters": {}
            }
            
            # 実行処理を開始
            await self.process_execution_message_internal(execution_data)
            
        except Exception as e:
            logger.error(f"Error in direct execution: {e}")
            execution_service = self.get_execution_service()
            await execution_service.update_execution_status(
                execution.execution_id,
                ExecutionStatus.FAILED,
                {
                    "current_step": f"直接実行エラー: {str(e)}",
                    "completed_steps": 0,
                    "percentage": 0.0
                }
            )

    async def process_execution_message(self, message):
        """実行メッセージを処理（Kafka経由）"""
        try:
            execution_data = message.value
            await self.process_execution_message_internal(execution_data)
            
        except Exception as e:
            logger.error(f"Error processing execution message: {e}")
            execution_data = getattr(message, 'value', {})
            execution_id = execution_data.get("execution_id")
            if execution_id:
                execution_service = self.get_execution_service()
                await execution_service.update_execution_status(
                    execution_id,
                    ExecutionStatus.FAILED,
                    {
                        "current_step": f"エラー: {str(e)}",
                        "completed_steps": 0,
                        "percentage": 0.0
                    }
                )

    async def process_execution_message_internal(self, execution_data):
        """実行メッセージの内部処理（共通ロジック）"""
        execution_id = execution_data.get("execution_id")
        pipeline_id = execution_data.get("pipeline_id")
        input_files = execution_data.get("input_files", [])
        parameters = execution_data.get("parameters", {})
        
        logger.info(f"Processing execution {execution_id} for pipeline {pipeline_id}")
        
        # 実行状況を「実行中」に更新
        execution_service = self.get_execution_service()
        await execution_service.update_execution_status(
            execution_id, 
            ExecutionStatus.RUNNING,
            {
                "current_step": "パイプライン処理開始",
                "completed_steps": 0,
                "percentage": 0.0
            }
        )
        
        try:
            # 実際の画像処理を実行
            await self.process_pipeline_components(execution_id, pipeline_id, input_files, parameters)
        except Exception as e:
            logger.error(f"Error in pipeline processing: {e}")
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                {
                    "current_step": f"パイプライン処理エラー: {str(e)}",
                    "completed_steps": 0,
                    "percentage": 0.0
                }
            )
    
    async def process_pipeline_components(self, execution_id: str, pipeline_id: str, input_files: list, parameters: dict):
        """パイプラインのコンポーネントを実際に処理"""
        try:
            execution_service = self.get_execution_service()
            
            # パイプライン情報を取得（モック）
            pipeline_components = self._get_mock_pipeline_components(pipeline_id)
            
            # 実行情報を更新
            execution = await execution_service.get_execution(execution_id)
            if execution:
                execution.progress.total_steps = len(pipeline_components)
                execution.steps = []
                
                # 各コンポーネントのステップを初期化
                for component in pipeline_components:
                    step = ExecutionStep(
                        component_name=component["name"],
                        status=StepStatus.PENDING
                    )
                    execution.steps.append(step)
            
            current_files = input_files
            all_output_files = []
            
            # 各コンポーネントを順次処理
            for i, component in enumerate(pipeline_components):
                component_name = component["name"]
                component_type = component["type"]
                component_params = component.get("parameters", {})
                
                # ステップ開始
                await execution_service.update_execution_status(
                    execution_id,
                    ExecutionStatus.RUNNING,
                    {
                        "current_step": f"{component_name} 処理中",
                        "completed_steps": i,
                        "percentage": (i / len(pipeline_components)) * 100
                    }
                )
                
                # 実行ステップを更新
                if execution and i < len(execution.steps):
                    execution.steps[i].status = StepStatus.RUNNING
                    execution.steps[i].started_at = datetime.utcnow()
                
                logger.info(f"Processing component {component_name} ({component_type})")
                
                try:
                    # コンポーネントを実際に処理
                    output_files = await self.component_service.process_component(
                        component_type, current_files, component_params
                    )
                    
                    # 出力ファイルを蓄積
                    all_output_files.extend(output_files)
                    
                    # 次のコンポーネントの入力として現在の出力を使用
                    current_files = [f.file_id for f in output_files]
                    
                    # ステップ完了
                    if execution and i < len(execution.steps):
                        execution.steps[i].status = StepStatus.COMPLETED
                        execution.steps[i].completed_at = datetime.utcnow()
                    
                    logger.info(f"Component {component_name} completed successfully, generated {len(output_files)} files")
                    
                    # 短い待機（UIの更新を確認できるように）
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing component {component_name}: {e}")
                    
                    # ステップ失敗
                    if execution and i < len(execution.steps):
                        execution.steps[i].status = StepStatus.FAILED
                        execution.steps[i].error_message = str(e)
                        execution.steps[i].completed_at = datetime.utcnow()
                    
                    # 処理を継続（他のコンポーネントも試行）
                    continue
            
            # 実行完了時に出力ファイルを設定
            if execution:
                execution.output_files = all_output_files
            
            # 最終ステータス更新
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.COMPLETED,
                {
                    "current_step": "パイプライン処理完了",
                    "completed_steps": len(pipeline_components),
                    "percentage": 100.0
                }
            )
            
            logger.info(f"Pipeline execution {execution_id} completed successfully with {len(all_output_files)} output files")
            
        except Exception as e:
            logger.error(f"Error in process_pipeline_components: {e}")
            execution_service = self.get_execution_service()
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                {
                    "current_step": f"パイプライン処理エラー: {str(e)}",
                    "completed_steps": 0,
                    "percentage": 0.0
                }
            )
    
    def _get_mock_pipeline_components(self, pipeline_id: str):
        """パイプラインのコンポーネント情報を取得（モック）"""
        # 実際の実装では、パイプラインサービスから取得する
        # ここでは簡単なモックを返す
        return [
            {
                "name": "リサイズ処理", 
                "type": "resize",
                "parameters": {"width": 800, "height": 600}
            },
            {
                "name": "物体検出", 
                "type": "ai_detection",
                "parameters": {"confidence": 0.5, "model": "yolov8n"}
            },
            {
                "name": "フィルタ処理", 
                "type": "filter",
                "parameters": {"filter_type": "blur"}
            }
        ]


# グローバルワーカーインスタンス
execution_worker = ExecutionWorker()
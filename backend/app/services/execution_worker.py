import asyncio
import json
import time
from typing import Dict, Any
from app.services.kafka_service import KafkaService
from app.models.execution import ExecutionStatus
import logging

logger = logging.getLogger(__name__)

class ExecutionWorker:
    def __init__(self):
        self.kafka_service = KafkaService()
        self.execution_service = None  # 遅延初期化
        self.running = False
        
    def get_execution_service(self):
        """ExecutionServiceを遅延初期化"""
        if self.execution_service is None:
            from app.services.execution_service import ExecutionService
            self.execution_service = ExecutionService()
        return self.execution_service
    
    async def start(self):
        """ワーカーを開始"""
        self.running = True
        logger.info("Execution worker started")
        
        # Kafkaコンシューマーでメッセージを処理
        await self.kafka_service.consume_messages(
            topics=["image-processing-requests"],
            message_handler=self.process_execution_message,
            group_id="execution-worker"
        )
    
    async def stop(self):
        """ワーカーを停止"""
        self.running = False
        logger.info("Execution worker stopped")
    
    async def process_execution_message(self, message):
        """実行メッセージを処理"""
        try:
            execution_data = message.value
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
                    "current_step": "画像処理開始",
                    "completed_steps": 1,
                    "percentage": 10.0
                }
            )
            
            # 実際の画像処理をシミュレート
            await self.simulate_image_processing(execution_id, input_files, parameters)
            
        except Exception as e:
            logger.error(f"Error processing execution message: {e}")
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
    
    async def simulate_image_processing(self, execution_id: str, input_files: list, parameters: dict):
        """画像処理をシミュレート（開発用）"""
        try:
            execution_service = self.get_execution_service()
            
            # ステップ1: ファイル読み込み
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": "ファイル読み込み中",
                    "completed_steps": 1,
                    "percentage": 25.0
                }
            )
            await asyncio.sleep(2)  # 2秒待機
            
            # ステップ2: 画像処理
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": "画像処理中",
                    "completed_steps": 2,
                    "percentage": 50.0
                }
            )
            await asyncio.sleep(3)  # 3秒待機
            
            # ステップ3: 結果保存
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": "結果保存中",
                    "completed_steps": 3,
                    "percentage": 75.0
                }
            )
            await asyncio.sleep(2)  # 2秒待機
            
            # 完了
            await execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.COMPLETED,
                {
                    "current_step": "完了",
                    "completed_steps": 4,
                    "percentage": 100.0
                }
            )
            
            logger.info(f"Execution {execution_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error in simulate_image_processing: {e}")
            await self.execution_service.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                {
                    "current_step": f"処理エラー: {str(e)}",
                    "completed_steps": 0,
                    "percentage": 0.0
                }
            )

# グローバルワーカーインスタンス
execution_worker = ExecutionWorker()
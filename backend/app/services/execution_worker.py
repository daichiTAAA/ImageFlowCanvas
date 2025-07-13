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
        from app.services.execution_service import get_global_execution_service
        return get_global_execution_service()
    
    async def start(self):
        """ワーカーを開始"""
        self.running = True
        logger.info("Execution worker started")
        print("Execution worker started - DEBUG")
        
        # 常に直接実行モードで開始（Kafkaの問題を回避）
        logger.info("Starting direct execution mode")
        print("Starting direct execution mode - DEBUG")
        
        try:
            await self.start_direct_execution_mode()
        except Exception as e:
            logger.error(f"Error starting direct execution mode: {e}")
            print(f"Error starting direct execution mode: {e} - DEBUG")
    
    async def stop(self):
        """ワーカーを停止"""
        self.running = False
        logger.info("Execution worker stopped")
    
    async def start_direct_execution_mode(self):
        """直接実行モード（Kafkaが利用できない場合）"""
        logger.info("Starting direct execution mode")
        print("Starting direct execution mode - DEBUG")
        execution_service = self.get_execution_service()
        
        # 実行待ちのタスクを定期的にチェック
        while self.running:
            try:
                print(f"Direct execution mode: checking for pending executions... - DEBUG")
                # 実行待ちのタスクがあるかチェック
                pending_executions = await execution_service.get_pending_executions()
                
                print(f"Found {len(pending_executions)} pending executions - DEBUG")
                
                if pending_executions:
                    logger.info(f"Found {len(pending_executions)} pending executions")
                    print(f"Found {len(pending_executions)} pending executions - DEBUG")
                
                for execution in pending_executions:
                    logger.info(f"Processing execution {execution.execution_id} in direct mode")
                    print(f"Processing execution {execution.execution_id} in direct mode - DEBUG")
                    await self.process_execution_direct(execution)
                
                # 5秒間隔でチェック
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in direct execution mode: {e}")
                print(f"Error in direct execution mode: {e} - DEBUG")
                await asyncio.sleep(10)  # エラー時は長めに待機
    
    async def process_execution_direct(self, execution):
        """直接実行モードでの実行処理"""
        print(f"process_execution_direct called for {execution.execution_id} - DEBUG")
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
            print(f"Error in direct execution: {e} - DEBUG")
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
        
        print(f"process_execution_message_internal called for {execution_id} - DEBUG")
        logger.info(f"Processing execution {execution_id} for pipeline {pipeline_id}")
        
        # 実行状況を「実行中」に更新
        execution_service = self.get_execution_service()
        print(f"Updating execution status to RUNNING - DEBUG")
        await execution_service.update_execution_status(
            execution_id, 
            ExecutionStatus.RUNNING,
            {
                "current_step": "画像処理開始",
                "completed_steps": 1,
                "percentage": 10.0
            }
        )
        
        print(f"Starting simulate_image_processing - DEBUG")
        # 実際の画像処理をシミュレート
        await self.simulate_image_processing(execution_id, input_files, parameters)
    
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
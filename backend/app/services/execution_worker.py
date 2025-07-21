import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.services.kafka_service import KafkaService
from app.services.grpc_pipeline_executor import get_grpc_pipeline_executor
from app.models.execution import ExecutionStatus, ExecutionStep, StepStatus, OutputFile
import logging

logger = logging.getLogger(__name__)


class ExecutionWorker:
    """
    Execution worker for direct gRPC pipeline processing
    Ultra-fast direct gRPC service calls for image processing
    """

    def __init__(self):
        self.kafka_service = KafkaService()
        self.grpc_executor = get_grpc_pipeline_executor()
        self.execution_service = None  # 遅延初期化
        self.running = False
        self.monitoring_interval = 5  # seconds for monitoring tasks

    def get_execution_service(self):
        """ExecutionServiceを遅延初期化"""
        from app.services.execution_service import get_global_execution_service

        return get_global_execution_service()

    async def start(self):
        """ワーカーを開始"""
        self.running = True
        logger.info("Execution worker started with direct gRPC pipeline execution")

        try:
            # Start monitoring tasks
            await asyncio.gather(
                self.start_direct_grpc_mode(), self.start_pipeline_monitoring()
            )
        except Exception as e:
            logger.error(f"Error in execution worker: {e}")

    async def stop(self):
        """ワーカーを停止"""
        self.running = False
        logger.info("Execution worker stopped")

        # Close gRPC connections
        await self.grpc_executor.close()

    async def start_direct_grpc_mode(self):
        """Direct gRPC execution mode - processes pipelines with direct gRPC calls"""
        logger.info("Starting direct gRPC pipeline execution mode")
        execution_service = self.get_execution_service()

        # Check for pending executions that need processing via Kafka
        # Note: Most executions now happen directly in ExecutionService,
        # this is for fallback scenarios
        while self.running:
            try:
                # Check for any pending executions from Kafka queue
                # This handles cases where direct execution fails and falls back to async processing
                await self.process_kafka_pipeline_requests()

                # Check for any stale pending executions that might need retry
                pending_executions = await execution_service.get_pending_executions()

                for execution in pending_executions:
                    # Check if execution has been pending too long (>30 seconds)
                    if hasattr(execution, "created_at"):
                        time_diff = (
                            datetime.now() - execution.created_at
                        ).total_seconds()
                        if time_diff > 30:
                            logger.warning(
                                f"Retrying stale execution {execution.execution_id}"
                            )
                            await self.retry_stale_execution(execution)

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in direct gRPC mode: {e}")
                await asyncio.sleep(10)

    async def start_pipeline_monitoring(self):
        """Pipeline monitoring mode - monitors gRPC service health and execution metrics"""
        logger.info("Starting pipeline monitoring mode")

        while self.running:
            try:
                # Monitor gRPC service health
                await self.monitor_grpc_services_health()

                # Monitor execution metrics and send to Kafka for observability
                await self.report_execution_metrics()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in pipeline monitoring: {e}")
                await asyncio.sleep(20)

    async def process_kafka_pipeline_requests(self):
        """Process pipeline execution requests from Kafka queue"""
        try:
            # This is a simplified implementation - in a real scenario,
            # you would consume from Kafka and process requests
            pass
        except Exception as e:
            logger.error(f"Error processing Kafka pipeline requests: {e}")

    async def retry_stale_execution(self, execution):
        """Retry executions that have been pending too long"""
        try:
            execution_service = self.get_execution_service()

            # Build pipeline config
            pipeline_config = {
                "pipelineId": execution.pipeline_id,
                "steps": self._get_default_pipeline_steps(),
                "globalParameters": {
                    "inputPath": execution.execution_id,  # Assuming this is the input file ID
                    "executionId": execution.execution_id,
                },
            }

            # Execute directly with gRPC
            result = await self.grpc_executor.execute_pipeline(
                pipeline_config, execution.execution_id
            )

            # Update execution status based on result
            if result["status"] == "completed":
                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.COMPLETED,
                    {
                        "current_step": "完了",
                        "completed_steps": 3,
                        "percentage": 100.0,
                        "execution_time_ms": result.get("execution_time_ms", 0),
                    },
                )
            else:
                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.FAILED,
                    {
                        "current_step": "失敗",
                        "error": result.get("error", "Unknown error"),
                    },
                )

        except Exception as e:
            logger.error(
                f"Error retrying stale execution {execution.execution_id}: {e}"
            )

    async def monitor_grpc_services_health(self):
        """Monitor health of gRPC services"""
        try:
            # Use the gRPC monitor service to check health
            from app.services.grpc_monitor_service import GRPCMonitorService

            monitor = GRPCMonitorService()

            health_statuses = await monitor.get_all_services_health()

            # Log any unhealthy services
            for status in health_statuses:
                if status.get("status") != "healthy":
                    logger.warning(
                        f"gRPC service {status.get('service_name')} is unhealthy: {status.get('error')}"
                    )

        except Exception as e:
            logger.error(f"Error monitoring gRPC service health: {e}")

    async def report_execution_metrics(self):
        """Report execution metrics for observability"""
        try:
            execution_service = self.get_execution_service()

            # Get metrics
            total_executions = len(execution_service.executions)
            pending_count = len(await execution_service.get_pending_executions())
            running_count = len(await execution_service.get_running_executions())

            # Send metrics to Kafka for monitoring dashboards
            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_executions": total_executions,
                "pending_executions": pending_count,
                "running_executions": running_count,
                "worker_mode": "direct_grpc",
            }

            await self.kafka_service.send_message("execution-metrics", metrics)

        except Exception as e:
            logger.error(f"Error reporting execution metrics: {e}")

    def _get_default_pipeline_steps(self):
        """Get default pipeline steps for retry scenarios"""
        return [
            {
                "stepId": "resize-step",
                "componentName": "resize",
                "parameters": {"width": 800, "height": 600},
                "dependencies": [],
            },
            {
                "stepId": "ai-detection-step",
                "componentName": "ai_detection",
                "parameters": {"model_name": "yolo", "confidence_threshold": 0.5},
                "dependencies": ["resize-step"],
            },
            {
                "stepId": "filter-step",
                "componentName": "filter",
                "parameters": {"filter_type": "gaussian", "intensity": 1.0},
                "dependencies": ["ai-detection-step"],
            },
        ]


# 全体的なexecution_workerインスタンス
execution_worker = ExecutionWorker()

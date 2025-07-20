import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from app.services.kafka_service import KafkaService
from app.services.argo_workflow_service import get_argo_workflow_service
from app.models.execution import ExecutionStatus, ExecutionStep, StepStatus, OutputFile
import logging

logger = logging.getLogger(__name__)


class ExecutionWorker:
    def __init__(self):
        self.kafka_service = KafkaService()
        self.argo_service = get_argo_workflow_service()
        self.execution_service = None  # 遅延初期化
        self.running = False
        self.workflow_monitor_interval = 10  # seconds

    def get_execution_service(self):
        """ExecutionServiceを遅延初期化"""
        from app.services.execution_service import get_global_execution_service

        return get_global_execution_service()

    async def start(self):
        """ワーカーを開始"""
        self.running = True
        logger.info("Execution worker started")

        # Argo Workflows delegationモードで開始
        logger.info("Starting Argo Workflows delegation mode")

        try:
            # 2つのタスクを並行実行
            await asyncio.gather(
                self.start_workflow_delegation_mode(), self.start_workflow_monitoring()
            )
        except Exception as e:
            logger.error(f"Error in execution worker: {e}")

    async def stop(self):
        """ワーカーを停止"""
        self.running = False
        logger.info("Execution worker stopped")

    async def start_workflow_delegation_mode(self):
        """ワークフロー委譲モード - Argo Workflowsに処理を委譲"""
        logger.info("Starting workflow delegation mode")
        execution_service = self.get_execution_service()

        # 実行待ちのタスクを定期的にチェック
        while self.running:
            try:
                # 実行待ちのタスクがあるかチェック
                pending_executions = await execution_service.get_pending_executions()

                if pending_executions:
                    logger.info(f"Found {len(pending_executions)} pending executions")

                for execution in pending_executions:
                    logger.info(
                        f"Delegating execution {execution.execution_id} to Argo Workflows"
                    )
                    await self.delegate_execution_to_argo(execution)

                # 5秒間隔でチェック
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in workflow delegation mode: {e}")
                await asyncio.sleep(10)  # エラー時は長めに待機

    async def start_workflow_monitoring(self):
        """ワークフロー監視モード - Argo Workflowsの進捗を監視"""
        logger.info("Starting workflow monitoring mode")
        execution_service = self.get_execution_service()

        while self.running:
            try:
                # 実行中のタスクを取得
                running_executions = await execution_service.get_running_executions()

                for execution in running_executions:
                    if hasattr(execution, "workflow_name") and execution.workflow_name:
                        await self.monitor_workflow_progress(execution)

                # 定期的に監視
                await asyncio.sleep(self.workflow_monitor_interval)

            except Exception as e:
                logger.error(f"Error in workflow monitoring: {e}")
                await asyncio.sleep(20)  # エラー時は長めに待機

    async def delegate_execution_to_argo(self, execution):
        """実行をArgo Workflowsに委譲、失敗時は詳細な情報を提供"""
        try:
            execution_service = self.get_execution_service()

            # 実行状況を「実行中」に更新
            await execution_service.update_execution_status(
                execution.execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": "Argo Workflowsへの接続を確認中",
                    "completed_steps": 0,
                    "percentage": 5.0,
                },
            )

            # パイプライン定義を取得（モック）
            pipeline_definition = self._get_mock_pipeline_definition(
                execution.pipeline_id
            )

            # 実行データを準備
            input_files = []  # 実際の実装では実行からファイルリストを取得
            parameters = {}  # 実際の実装では実行から設定を取得

            # 実行状況を更新
            await execution_service.update_execution_status(
                execution.execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": "Argo Workflowsに処理を委譲中",
                    "completed_steps": 0,
                    "percentage": 10.0,
                },
            )

            # Argo Workflowsにワークフローを送信
            workflow_name = await self.argo_service.submit_pipeline_workflow(
                execution_id=execution.execution_id,
                pipeline_id=execution.pipeline_id,
                input_files=input_files,
                pipeline_definition=pipeline_definition,
                parameters=parameters,
            )

            if workflow_name:
                # ワークフロー名を実行情報に保存
                execution.workflow_name = workflow_name
                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.RUNNING,
                    {
                        "current_step": f"Argo Workflow {workflow_name} が開始されました",
                        "completed_steps": 1,
                        "percentage": 20.0,
                        "workflow_name": workflow_name,
                    },
                )
                logger.info(
                    f"Successfully delegated execution {execution.execution_id} to workflow {workflow_name}"
                )
            else:
                # ワークフロー送信失敗 - 詳細エラー情報とフォールバック案内
                error_message = "Argo Workflowsへの委譲に失敗しました"

                # Argo Workflowsの健全性チェック
                is_healthy = await self.argo_service.health_check()
                if not is_healthy:
                    error_message = "Argo Workflowsサーバーに接続できません。サーバーが起動していることを確認してください。"

                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.FAILED,
                    {
                        "current_step": error_message,
                        "completed_steps": 0,
                        "percentage": 0.0,
                        "error_details": {
                            "error_type": "argo_delegation_failure",
                            "argo_server_url": self.argo_service.argo_server_url,
                            "argo_namespace": self.argo_service.namespace,
                            "workflow_template": self.argo_service.workflow_template,
                            "argo_server_healthy": is_healthy,
                        },
                    },
                )
                logger.error(
                    f"Failed to delegate execution {execution.execution_id} to Argo Workflows"
                )

                # フォールバック処理の提案をログに記録
                logger.info(
                    f"Consider implementing fallback execution mode for execution {execution.execution_id}"
                )

        except Exception as e:
            logger.error(f"Error delegating execution to Argo: {e}")
            execution_service = self.get_execution_service()
            await execution_service.update_execution_status(
                execution.execution_id,
                ExecutionStatus.FAILED,
                {
                    "current_step": f"Argo委譲エラー: {str(e)}",
                    "completed_steps": 0,
                    "percentage": 0.0,
                    "error_details": {
                        "error_type": "argo_delegation_exception",
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
            )

    async def monitor_workflow_progress(self, execution):
        """ワークフローの進捗を監視（エラーハンドリング強化）"""
        try:
            execution_service = self.get_execution_service()
            workflow_name = execution.workflow_name

            logger.debug(
                f"Monitoring workflow {workflow_name} for execution {execution.execution_id}"
            )

            # Argo Workflowsから状態を取得
            workflow_status = await self.argo_service.get_workflow_status(workflow_name)

            if not workflow_status:
                logger.warning(f"Could not get status for workflow {workflow_name}")
                # 一定回数失敗した場合はエラーにする処理を追加可能
                return

            # ワークフロー状態を解析
            status = workflow_status.get("status", {})
            phase = status.get("phase", "Unknown")
            start_time = workflow_status.get("metadata", {}).get("creationTimestamp")

            logger.debug(f"Workflow {workflow_name} phase: {phase}")

            # 進捗情報を更新
            if phase == "Pending":
                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.RUNNING,
                    {
                        "current_step": "ワークフロー開始待機中",
                        "completed_steps": 1,
                        "percentage": 15.0,
                    },
                )
            elif phase == "Running":
                progress_info = self._calculate_workflow_progress(status)
                await execution_service.update_execution_status(
                    execution.execution_id, ExecutionStatus.RUNNING, progress_info
                )
            elif phase == "Succeeded":
                # ワークフロー完了後の出力ファイル発見
                output_files = await self._discover_output_files(execution.execution_id)
                steps = await self._extract_step_details(workflow_name, status)
                
                # ステップの実行結果をチェックして実際の成功/失敗を判定
                has_processing_failures = self._check_for_processing_failures(status)
                
                if has_processing_failures:
                    # ワークフローは成功したが、処理内容が失敗している場合
                    error_details = self._extract_processing_error_details(status)
                    await execution_service.update_execution_status(
                        execution.execution_id,
                        ExecutionStatus.FAILED,
                        {
                            "current_step": f"処理エラー: {error_details.get('summary', '画像処理に失敗しました')}",
                            "completed_steps": 0,
                            "percentage": 0.0,
                            "error_details": {
                                "phase": phase,
                                "processing_errors": error_details,
                                "workflow_name": workflow_name,
                            },
                        },
                    )
                    logger.error(f"Workflow {workflow_name} completed but processing failed: {error_details}")
                else:
                    # 正常に完了
                    await execution_service.update_execution_status(
                        execution.execution_id,
                        ExecutionStatus.COMPLETED,
                        {
                            "current_step": "ワークフロー処理完了",
                            "completed_steps": 100,
                            "percentage": 100.0,
                            "completed_at": datetime.utcnow().isoformat(),
                        },
                    )
                    logger.info(
                        f"Workflow {workflow_name} completed successfully with {len(output_files)} output files"
                    )

                # 出力ファイルとステップ詳細を更新
                await self._update_execution_artifacts(
                    execution.execution_id, output_files, steps
                )
            elif phase == "Failed" or phase == "Error":
                error_message = status.get("message", "Unknown error")
                failed_nodes = self._get_failed_nodes(status)

                await execution_service.update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.FAILED,
                    {
                        "current_step": f"ワークフロー処理失敗: {error_message}",
                        "completed_steps": 0,
                        "percentage": 0.0,
                        "error_details": {
                            "phase": phase,
                            "message": error_message,
                            "failed_nodes": failed_nodes,
                            "workflow_name": workflow_name,
                        },
                    },
                )
                logger.error(f"Workflow {workflow_name} failed: {error_message}")
                if failed_nodes:
                    logger.error(f"Failed nodes: {failed_nodes}")
            else:
                logger.warning(f"Unknown workflow phase for {workflow_name}: {phase}")

        except Exception as e:
            logger.error(f"Error monitoring workflow progress: {e}")
            # 監視エラーが発生しても実行を失敗にはしない（一時的な問題の可能性）
            execution_service = self.get_execution_service()
            await execution_service.update_execution_status(
                execution.execution_id,
                ExecutionStatus.RUNNING,
                {
                    "current_step": f"ワークフロー監視エラー（再試行中）: {str(e)}",
                    "completed_steps": execution.progress.completed_steps,
                    "percentage": execution.progress.percentage,
                },
            )

    def _get_failed_nodes(
        self, workflow_status: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """ワークフロー状態から失敗したノードの情報を取得"""
        nodes = workflow_status.get("nodes", {})
        failed_nodes = []

        for node_id, node in nodes.items():
            node_phase = node.get("phase", "")
            if node_phase in ["Failed", "Error"]:
                failed_nodes.append(
                    {
                        "name": node.get("displayName", node.get("name", "unknown")),
                        "phase": node_phase,
                        "message": node.get("message", "No error message"),
                        "started_at": node.get("startedAt", ""),
                        "finished_at": node.get("finishedAt", ""),
                    }
                )

        return failed_nodes

    def _check_for_processing_failures(self, workflow_status: Dict[str, Any]) -> bool:
        """ワークフロー内の処理結果から失敗をチェック"""
        try:
            nodes = workflow_status.get("nodes", {})
            logger.info(f"Checking {len(nodes)} nodes for processing failures")
            
            for node_id, node in nodes.items():
                # HTTP テンプレートのノードのみをチェック（gRPCサービス呼び出し）
                node_type = node.get("type", "")
                if node_type == "HTTP":
                    logger.info(f"Checking HTTP node: {node.get('displayName', node_id)}")
                    
                    # ノードの出力結果をチェック - outputs.resultに直接格納されている
                    outputs = node.get("outputs", {})
                    result_value = outputs.get("result", "")
                    
                    if result_value:
                        logger.info(f"Node result: {result_value[:200]}...")
                        try:
                            result_json = json.loads(result_value)
                            result_data = result_json.get("result", {})
                            status_value = result_data.get("status", "")
                            
                            logger.info(f"Parsed status: {status_value}")
                            # PROCESSING_STATUS_FAILED をチェック
                            if status_value == "PROCESSING_STATUS_FAILED":
                                logger.warning(f"Found processing failure in node {node_id}")
                                return True
                        except json.JSONDecodeError:
                            # JSON解析失敗の場合はエラーメッセージ文字列をチェック
                            logger.warning(f"JSON decode failed for node {node_id}, checking string content")
                            if "PROCESSING_STATUS_FAILED" in result_value:
                                logger.warning(f"Found PROCESSING_STATUS_FAILED in string content for node {node_id}")
                                return True
                            if "NoSuchKey" in result_value or "Object does not exist" in result_value:
                                logger.warning(f"Found file not found error in node {node_id}")
                                return True
                                        
            logger.info("No processing failures detected")
            return False
        except Exception as e:
            logger.warning(f"Error checking for processing failures: {e}")
            return False

    def _extract_processing_error_details(self, workflow_status: Dict[str, Any]) -> Dict[str, Any]:
        """処理エラーの詳細を抽出"""
        error_details = {
            "summary": "画像処理に失敗しました",
            "errors": [],
            "missing_files": [],
        }
        
        try:
            nodes = workflow_status.get("nodes", {})
            
            for node_id, node in nodes.items():
                node_type = node.get("type", "")
                if node_type == "HTTP":
                    node_name = node.get("displayName", node.get("name", "unknown"))
                    outputs = node.get("outputs", {})
                    result_value = outputs.get("result", "")
                    
                    if result_value:
                        try:
                            result_json = json.loads(result_value)
                            result_data = result_json.get("result", {})
                            status_value = result_data.get("status", "")
                            message = result_data.get("message", "")
                            
                            if status_value == "PROCESSING_STATUS_FAILED":
                                error_info = {
                                    "step": node_name,
                                    "message": message,
                                    "status": status_value
                                }
                                error_details["errors"].append(error_info)
                                
                                # ファイル不存在エラーの場合
                                if "NoSuchKey" in message or "Object does not exist" in message:
                                    # ファイル名を抽出
                                    if "object_name:" in message:
                                        filename = message.split("object_name:")[-1].strip().rstrip(',')
                                        error_details["missing_files"].append(filename)
                                    # resource: パターンからもファイル名を抽出
                                    elif "resource:" in message:
                                        resource_part = message.split("resource:")[-1].split(",")[0].strip()
                                        filename = resource_part.split("/")[-1]
                                        error_details["missing_files"].append(filename)
                                        
                        except json.JSONDecodeError:
                            # JSON解析失敗の場合は文字列として処理
                            if "PROCESSING_STATUS_FAILED" in result_value:
                                error_details["errors"].append({
                                    "step": node_name,
                                    "message": result_value,
                                    "status": "FAILED"
                                })
                                        
            # エラーサマリーを生成
            if error_details["missing_files"]:
                error_details["summary"] = f"入力ファイルが見つかりません: {', '.join(error_details['missing_files'][:3])}"
            elif error_details["errors"]:
                first_error = error_details["errors"][0]
                error_details["summary"] = f"{first_error['step']}: {first_error['message'][:100]}"
                
        except Exception as e:
            logger.warning(f"Error extracting processing error details: {e}")
            error_details["summary"] = f"エラー詳細の取得に失敗: {str(e)}"
            
        return error_details

    def _calculate_workflow_progress(
        self, workflow_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ワークフロー状態から進捗情報を計算（改良版）"""
        nodes = workflow_status.get("nodes", {})

        total_nodes = len(nodes)
        completed_nodes = 0
        running_nodes = 0
        current_step = "処理中"

        for node_id, node in nodes.items():
            node_phase = node.get("phase", "")
            node_name = node.get("displayName", node.get("name", "unknown"))

            if node_phase == "Succeeded":
                completed_nodes += 1
            elif node_phase == "Running":
                running_nodes += 1
                current_step = f"{node_name} 実行中"
            elif node_phase == "Failed":
                current_step = f"{node_name} 失敗"
                break  # 失敗ノードがあれば優先的に表示

        # より詳細な進捗計算
        if total_nodes > 0:
            base_percentage = (completed_nodes / total_nodes) * 80  # 80%まで
            if running_nodes > 0:
                base_percentage += 10  # 実行中のノードがあれば+10%
        else:
            base_percentage = 50  # ノード情報がない場合は50%

        # 最低20%は確保（ワークフローが開始されている証拠）
        percentage = max(20.0, min(95.0, base_percentage))

        return {
            "current_step": current_step,
            "completed_steps": completed_nodes,
            "total_steps": total_nodes,
            "percentage": percentage,
            "running_nodes": running_nodes,
        }

    async def process_execution_message(self, message):
        """実行メッセージを処理（Kafka経由）"""
        try:
            execution_data = message.value
            execution_id = execution_data.get("execution_id")

            # Kafka経由の場合もArgo Workflowsに委譲
            logger.info(
                f"Received Kafka execution message for {execution_id}, delegating to Argo Workflows"
            )

            # 実行情報を取得
            execution_service = self.get_execution_service()
            execution = await execution_service.get_execution(execution_id)

            if execution:
                await self.delegate_execution_to_argo(execution)
            else:
                logger.error(f"Execution {execution_id} not found")

        except Exception as e:
            logger.error(f"Error processing execution message: {e}")
            execution_data = getattr(message, "value", {})
            execution_id = execution_data.get("execution_id")
            if execution_id:
                execution_service = self.get_execution_service()
                await execution_service.update_execution_status(
                    execution_id,
                    ExecutionStatus.FAILED,
                    {
                        "current_step": f"メッセージ処理エラー: {str(e)}",
                        "completed_steps": 0,
                        "percentage": 0.0,
                    },
                )

    def _get_mock_pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        """パイプライン定義を取得（モック）"""
        # 実際の実装では、パイプラインサービスから取得する
        return {
            "components": [
                {
                    "name": "resize",
                    "type": "resize",
                    "parameters": {
                        "width": 800,
                        "height": 600,
                        "maintain_aspect": True,
                    },
                },
                {
                    "name": "ai_detection",
                    "type": "ai_detection",
                    "parameters": {
                        "confidence": 0.5,
                        "model": "yolo11n.pt",
                        "draw_boxes": True,
                    },
                    "dependencies": ["resize"],
                },
                {
                    "name": "filter",
                    "type": "filter",
                    "parameters": {"filter_type": "blur", "intensity": 1.0},
                    "dependencies": ["ai_detection"],
                },
            ]
        }

    async def _discover_output_files(self, execution_id: str) -> List[OutputFile]:
        """実行IDに基づいてMinIOから出力ファイルを発見"""
        output_files = []
        try:
            # FileServiceを使用してMinIOから実際のファイルを検索
            from app.services.file_service import FileService

            file_service = FileService()

            if file_service.minio_available:
                # MinIO接続が利用可能な場合、実際のファイルを検索
                discovered_files = await self._search_minio_files(
                    file_service, execution_id
                )
                output_files = discovered_files
                logger.info(
                    f"Discovered {len(output_files)} output files for execution {execution_id}"
                )
            else:
                # MinIO接続が利用不可の場合、モック実装
                logger.warning(
                    f"MinIO not available, using mock output files for {execution_id}"
                )
                expected_outputs = [
                    f"{execution_id}_resize.png",
                    f"{execution_id}_ai-detection.png",
                    f"{execution_id}_filter.png",
                ]

                for i, filename in enumerate(expected_outputs):
                    output_files.append(
                        OutputFile(
                            file_id=f"{execution_id}-output-{i}",
                            filename=filename,
                            file_size=500000,  # モックサイズ
                            content_type="image/png",
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to discover output files for {execution_id}: {e}")

        return output_files

    async def _search_minio_files(
        self, file_service, execution_id: str
    ) -> List[OutputFile]:
        """MinIOから実行IDに関連するファイルを検索"""
        output_files = []
        try:
            # MinIOクライアントから実行IDをプレフィックスとするオブジェクトを検索
            objects = file_service.minio_client.list_objects(
                bucket_name=file_service.bucket_name,
                prefix=f"{execution_id}",
                recursive=True,
            )

            for obj in objects:
                # オブジェクトの統計情報を取得
                stat = file_service.minio_client.stat_object(
                    bucket_name=file_service.bucket_name, object_name=obj.object_name
                )

                # ファイル拡張子からコンテンツタイプを推定
                content_type = "application/octet-stream"
                if obj.object_name.lower().endswith(".png"):
                    content_type = "image/png"
                elif obj.object_name.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif obj.object_name.lower().endswith(".tiff"):
                    content_type = "image/tiff"
                elif obj.object_name.lower().endswith(".json"):
                    content_type = "application/json"

                output_files.append(
                    OutputFile(
                        file_id=obj.object_name,  # 実際のオブジェクト名をfile_idとして使用
                        filename=obj.object_name,
                        file_size=stat.size,
                        content_type=content_type,
                    )
                )

        except Exception as e:
            logger.error(f"Error searching MinIO files for {execution_id}: {e}")

        return output_files

    async def _extract_step_details(
        self, workflow_name: str, status: Dict[str, Any]
    ) -> List[ExecutionStep]:
        """ワークフローステータスからステップ詳細を抽出（改良版）"""
        steps = []
        try:
            nodes = status.get("nodes", {})
            step_counter = 1

            # ノードをタイムスタンプでソート（実行順序を保持）
            sorted_nodes = sorted(
                nodes.items(), key=lambda x: x[1].get("startedAt", "")
            )

            for node_name, node_info in sorted_nodes:
                node_type = node_info.get("type", "")
                node_phase = node_info.get("phase", "")

                # Pod型のノードのみをステップとして扱う（DAGやTaskGroupは除外）
                if node_type == "Pod":
                    # ステップ名をより分かりやすく変換
                    display_name = node_info.get("displayName", node_name)
                    step_name = self._format_step_name(display_name, node_name)

                    # ステップ状態をマッピング
                    step_status = self._map_node_phase_to_step_status(node_phase)

                    # ログとアウトプットを取得
                    logs = await self._get_node_logs(workflow_name, node_name)
                    outputs = node_info.get("outputs", {})

                    step = ExecutionStep(
                        step_id=f"step-{step_counter}",
                        name=step_name,
                        component_name=step_name,  # フロントエンド互換性のため
                        status=step_status,
                        started_at=node_info.get("startedAt"),
                        completed_at=node_info.get("finishedAt"),
                        output_data={
                            "exit_code": outputs.get("exitCode", 0),
                            "logs": logs[:1000] if logs else "",  # 最初の1000文字のみ
                            "node_name": node_name,
                            "phase": node_phase,
                            "message": node_info.get("message", ""),
                        },
                        resource_usage={  # フロントエンド互換性のため
                            "exit_code": outputs.get("exitCode", 0),
                            "logs": logs[:1000] if logs else "",
                            "node_name": node_name,
                            "phase": node_phase,
                            "message": node_info.get("message", ""),
                        },
                    )
                    steps.append(step)
                    step_counter += 1

        except Exception as e:
            logger.warning(f"Failed to extract step details from {workflow_name}: {e}")

        return steps

    def _format_step_name(self, display_name: str, node_name: str) -> str:
        """ステップ名を分かりやすい形式にフォーマット"""
        # 既知のステップタイプを日本語名にマッピング
        step_mappings = {
            "resize": "画像リサイズ",
            "ai-detection": "AI物体検出",
            "filter": "画像フィルタ",
            "upload": "ファイルアップロード",
            "download": "ファイルダウンロード",
        }

        # display_nameまたはnode_nameから適切な名前を選択
        for key, japanese_name in step_mappings.items():
            if key in display_name.lower() or key in node_name.lower():
                return japanese_name

        # マッピングが見つからない場合はdisplay_nameをそのまま使用
        return display_name or node_name

    def _map_node_phase_to_step_status(self, node_phase: str) -> StepStatus:
        """ArgoワークフローのノードフェーズをExecutionStepのステータスにマッピング"""
        phase_mapping = {
            "Pending": StepStatus.PENDING,
            "Running": StepStatus.RUNNING,
            "Succeeded": StepStatus.COMPLETED,
            "Failed": StepStatus.FAILED,
            "Error": StepStatus.FAILED,
            "Skipped": StepStatus.SKIPPED,
        }
        return phase_mapping.get(node_phase, StepStatus.PENDING)

    async def _get_node_logs(self, workflow_name: str, node_name: str) -> str:
        """ワークフローノードのログを取得"""
        try:
            # Argo Workflowサービスにログ取得メソッドがない場合はスキップ
            if hasattr(self.argo_service, "get_workflow_logs"):
                logs = await self.argo_service.get_workflow_logs(
                    workflow_name, node_name
                )
                return logs
            else:
                logger.debug(
                    f"Argo service does not support log retrieval for {workflow_name}/{node_name}"
                )
                return ""
        except Exception as e:
            logger.debug(f"Could not get logs for {workflow_name}/{node_name}: {e}")
            return ""

    async def _update_execution_artifacts(
        self,
        execution_id: str,
        output_files: List[OutputFile],
        steps: List[ExecutionStep],
    ):
        """実行の成果物とステップ詳細を更新"""
        try:
            execution_service = self.get_execution_service()
            execution = await execution_service.get_execution(execution_id)
            if execution:
                # 実行オブジェクトを更新
                execution.output_files = output_files
                execution.steps = steps

                # WebSocket経由でフロントエンドに更新を通知
                websocket_manager = execution_service.get_websocket_manager()
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_execution_update(
                            execution_id,
                            {
                                "output_files": [file.dict() for file in output_files],
                                "steps": [step.dict() for step in steps],
                                "artifacts_updated": True,
                            },
                        )
                        logger.info(
                            f"Broadcasted artifact updates for execution {execution_id}"
                        )
                    except Exception as ws_error:
                        logger.warning(
                            f"Failed to broadcast execution update: {ws_error}"
                        )

                logger.info(
                    f"Updated execution {execution_id} with {len(output_files)} files and {len(steps)} steps"
                )

                # 将来的にデータベース永続化を実装する場合のプレースホルダー
                # await self._persist_execution_artifacts(execution_id, output_files, steps)

        except Exception as e:
            logger.error(
                f"Failed to update execution artifacts for {execution_id}: {e}"
            )

    async def _persist_execution_artifacts(
        self,
        execution_id: str,
        output_files: List[OutputFile],
        steps: List[ExecutionStep],
    ):
        """実行成果物をデータベースに永続化（将来の実装用プレースホルダー）"""
        # TODO: データベースモデルが実装されたら永続化処理を追加
        logger.debug(
            f"Database persistence not yet implemented for execution {execution_id}"
        )
        pass


# グローバルワーカーインスタンス
execution_worker = ExecutionWorker()

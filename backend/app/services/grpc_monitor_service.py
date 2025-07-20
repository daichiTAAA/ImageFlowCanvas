import asyncio
import logging
import grpc
import time
import sys
import os
from typing import Dict, Any, List, Optional
import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Add generated proto path
sys.path.append("/app")
from imageflow.v1 import (
    common_pb2,
    ai_detection_pb2_grpc,
    resize_pb2_grpc,
    filter_pb2_grpc,
)

logger = logging.getLogger(__name__)


class GRPCMonitorService:
    """常駐gRPCサービスの監視と管理を行うサービス"""

    def __init__(self):
        self.services = {
            "resize-grpc-service": {
                "name": "Image Resize Service",
                "endpoint": "resize-grpc-service.image-processing.svc.cluster.local:9090",
                "namespace": "image-processing",
                "deployment": "resize-grpc-service",
            },
            "ai-detection-grpc-service": {
                "name": "AI Detection Service",
                "endpoint": "ai-detection-grpc-service.image-processing.svc.cluster.local:9090",
                "namespace": "image-processing",
                "deployment": "ai-detection-grpc-service",
            },
            "filter-grpc-service": {
                "name": "Filter Service",
                "endpoint": "filter-grpc-service.image-processing.svc.cluster.local:9090",
                "namespace": "image-processing",
                "deployment": "filter-grpc-service",
            },
        }

        # Kubernetesクライアント初期化
        try:
            from kubernetes import config

            config.load_incluster_config()
            self.k8s_apps_v1 = k8s_client.AppsV1Api()
            self.k8s_core_v1 = k8s_client.CoreV1Api()
        except Exception as e:
            logger.warning(f"Failed to initialize Kubernetes client: {e}")
            self.k8s_apps_v1 = None
            self.k8s_core_v1 = None

    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """指定されたgRPCサービスのヘルスチェックを実行"""
        start_time = time.time()

        try:
            service_config = self.services.get(service_name)
            if not service_config:
                return {
                    "status": "UNKNOWN",
                    "error": f"Unknown service: {service_name}",
                    "response_time_ms": 0,
                }

            endpoint = service_config["endpoint"]

            # gRPCチャンネルを作成
            channel = grpc.insecure_channel(
                endpoint,
                options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 5000),
                    ("grpc.keepalive_permit_without_calls", True),
                    ("grpc.http2.keepalive_timeout_ms", 5000),
                    ("grpc.max_connection_idle_ms", 10000),
                ],
            )

            try:
                # 標準のgRPCヘルスチェックサービスを使用
                health_stub = health_pb2_grpc.HealthStub(channel)

                # 標準ヘルスチェックリクエストを作成
                health_request = health_pb2.HealthCheckRequest()
                # Empty service name for overall service health
                health_request.service = ""

                # タイムアウト付きでヘルスチェックを実行
                health_response = health_stub.Check(health_request, timeout=10.0)

                response_time_ms = (time.time() - start_time) * 1000

                # レスポンスのステータスを確認
                if health_response.status == health_pb2.HealthCheckResponse.SERVING:
                    return {
                        "service_name": service_name,
                        "display_name": service_config["name"],
                        "status": "SERVING",
                        "response_time_ms": round(response_time_ms, 2),
                        "endpoint": endpoint,
                        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    }
                else:
                    status_name = health_pb2.HealthCheckResponse.ServingStatus.Name(health_response.status)
                    return {
                        "service_name": service_name,
                        "display_name": service_config["name"],
                        "status": "NOT_SERVING",
                        "response_time_ms": round(response_time_ms, 2),
                        "endpoint": endpoint,
                        "error": f"Service reported status: {status_name}",
                        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    }

            except grpc.RpcError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_code = e.code()
                error_details = e.details()

                logger.error(
                    f"gRPC health check failed for {service_name}: {error_code} - {error_details}"
                )

                return {
                    "service_name": service_name,
                    "display_name": service_config["name"],
                    "status": "NOT_SERVING",
                    "error": f"gRPC error: {error_code} - {error_details}",
                    "response_time_ms": round(response_time_ms, 2),
                    "endpoint": endpoint,
                    "last_checked": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                }

            finally:
                channel.close()

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Unexpected error during health check for {service_name}: {str(e)}"
            )
            return {
                "service_name": service_name,
                "display_name": self.services.get(service_name, {}).get("name", service_name),
                "status": "ERROR",
                "error": f"Unexpected error: {str(e)}",
                "response_time_ms": round(response_time_ms, 2),
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            }

    async def get_all_services_health(self) -> List[Dict[str, Any]]:
        """全てのgRPCサービスの健康状態を並行してチェック"""
        tasks = []
        for service_name in self.services.keys():
            task = asyncio.create_task(self.check_service_health(service_name))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外が発生した場合はエラー情報を返す
        health_statuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = list(self.services.keys())[i]
                health_statuses.append(
                    {
                        "service_name": service_name,
                        "display_name": self.services[service_name]["name"],
                        "status": "error",
                        "error": str(result),
                        "last_checked": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime()
                        ),
                    }
                )
            else:
                health_statuses.append(result)

        return health_statuses

    async def get_services_info(self) -> List[Dict[str, Any]]:
        """サービス情報とパフォーマンスメトリクスを取得"""
        health_statuses = await self.get_all_services_health()

        services_info = []
        for health_status in health_statuses:
            if health_status:
                service_info = {
                    **health_status,
                    "uptime": await self._get_service_uptime(
                        health_status["service_name"]
                    ),
                    "request_count": await self._get_request_metrics(
                        health_status["service_name"]
                    ),
                    "cpu_usage": await self._get_cpu_usage(
                        health_status["service_name"]
                    ),
                    "memory_usage": await self._get_memory_usage(
                        health_status["service_name"]
                    ),
                }
                services_info.append(service_info)

        return services_info

    async def restart_service(self, service_name: str) -> bool:
        """gRPCサービスを再起動"""
        if service_name not in self.services:
            return False

        if not self.k8s_apps_v1:
            logger.error("Kubernetes client not available")
            return False

        try:
            service_info = self.services[service_name]
            namespace = service_info["namespace"]
            deployment_name = service_info["deployment"]

            # デプロイメントの再起動（replicas を 0 にしてから戻す）
            deployment = self.k8s_apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )

            original_replicas = deployment.spec.replicas

            # レプリカを0に設定
            deployment.spec.replicas = 0
            self.k8s_apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=deployment
            )

            # 少し待機
            await asyncio.sleep(2)

            # レプリカを元に戻す
            deployment.spec.replicas = original_replicas
            self.k8s_apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=deployment
            )

            logger.info(f"Restarted service: {service_name}")
            return True

        except ApiException as e:
            logger.error(f"Failed to restart service {service_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error restarting service {service_name}: {e}")
            return False

    async def _get_pod_info(self, service_info: Dict[str, Any]) -> Dict[str, Any]:
        """ポッド情報を取得"""
        if not self.k8s_core_v1:
            return {}

        try:
            namespace = service_info["namespace"]
            deployment_name = service_info["deployment"]

            # ラベルセレクタでポッドを検索
            label_selector = f"app={deployment_name.replace('-deployment', '')}"
            pods = self.k8s_core_v1.list_namespaced_pod(
                namespace=namespace, label_selector=label_selector
            )

            if pods.items:
                pod = pods.items[0]  # 最初のポッドを取得
                return {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "restart_count": sum(
                        [
                            container.restart_count
                            for container in pod.status.container_statuses or []
                        ]
                    ),
                    "created_time": (
                        pod.metadata.creation_timestamp.isoformat()
                        if pod.metadata.creation_timestamp
                        else None
                    ),
                    "node_name": pod.spec.node_name,
                }

        except Exception as e:
            logger.error(f"Failed to get pod info: {e}")

        return {}

    async def _get_service_uptime(self, service_name: str) -> Optional[str]:
        """サービスのアップタイムを取得"""
        # 実装簡略化：実際は Prometheus メトリクスから取得
        return "24h 30m"

    async def _get_request_metrics(self, service_name: str) -> Dict[str, Any]:
        """リクエストメトリクスを取得"""
        # 実装簡略化：実際は Prometheus メトリクスから取得
        return {
            "total_requests": 1234,
            "requests_per_minute": 15.2,
            "success_rate": 99.5,
        }

    async def _get_cpu_usage(self, service_name: str) -> Optional[str]:
        """CPU使用率を取得"""
        # 実装簡略化：実際は Kubernetes メトリクスから取得
        return "45%"

    async def _get_memory_usage(self, service_name: str) -> Optional[str]:
        """メモリ使用率を取得"""
        # 実装簡略化：実際は Kubernetes メトリクスから取得
        return "128/256 MB"

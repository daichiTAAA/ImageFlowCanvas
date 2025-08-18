import asyncio
import logging
import grpc
import time
import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Kubernetes関連のインポートは条件付き
try:
    import kubernetes.client as k8s_client
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    k8s_client = None
    ApiException = Exception
    KUBERNETES_AVAILABLE = False

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc

    GRPC_HEALTH_AVAILABLE = True
except ImportError:
    health_pb2 = None
    health_pb2_grpc = None
    GRPC_HEALTH_AVAILABLE = False

# Add generated proto path
sys.path.append("/app")
from imageflow.v1 import (
    common_pb2,
    ai_detection_pb2_grpc,
    resize_pb2_grpc,
    filter_pb2_grpc,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GRPCMonitorService:
    """常駐gRPCサービスの監視と管理を行うサービス"""

    def __init__(self):
        # 環境変数で実行環境を判定
        is_nomad = os.getenv("NOMAD_ALLOC_ID") is not None
        is_compose = (
            os.getenv("COMPOSE_PROJECT_NAME") is not None
            or os.getenv("DOCKER_COMPOSE") is not None
        )

        # 環境判定のログ出力
        logger.info(
            f"Environment detection - NOMAD_ALLOC_ID: {os.getenv('NOMAD_ALLOC_ID')}"
        )
        logger.info(
            f"Environment detection - COMPOSE_PROJECT_NAME: {os.getenv('COMPOSE_PROJECT_NAME')}"
        )
        logger.info(
            f"Environment detection - DOCKER_COMPOSE: {os.getenv('DOCKER_COMPOSE')}"
        )
        logger.info(
            f"Environment detection - is_nomad: {is_nomad}, is_compose: {is_compose}"
        )

        if is_nomad:
            # Nomad環境用のサービス設定
            self.services = {
                "resize-grpc-service": {
                    "name": "Image Resize Service",
                    "endpoint": "192.168.5.15:9090",
                    "namespace": None,
                    "deployment": "resize-grpc-service",
                },
                "ai-detection-grpc-service": {
                    "name": "AI Detection Service",
                    "endpoint": "192.168.5.15:9091",
                    "namespace": None,
                    "deployment": "ai-detection-grpc-service",
                },
                "filter-grpc-service": {
                    "name": "Filter Service",
                    "endpoint": "192.168.5.15:9093",
                    "namespace": None,
                    "deployment": "filter-grpc-service",
                },
            }
            self.environment = "nomad"
            logger.info("Detected Nomad environment - using Consul service discovery")
        elif is_compose:
            # Docker Compose環境用のサービス設定
            self.services = {
                "resize-grpc": {
                    "name": "Image Resize Service",
                    "endpoint": "resize-grpc:9090",
                    "namespace": None,
                    "deployment": "resize-grpc",
                },
                "ai-detection-grpc": {
                    "name": "AI Detection Service",
                    "endpoint": "ai-detection-grpc:9090",
                    "namespace": None,
                    "deployment": "ai-detection-grpc",
                },
                "filter-grpc": {
                    "name": "Filter Service",
                    "endpoint": "filter-grpc:9090",
                    "namespace": None,
                    "deployment": "filter-grpc",
                },
                "camera-stream-grpc": {
                    "name": "Camera Stream Service",
                    "endpoint": "camera-stream-grpc:9090",
                    "namespace": None,
                    "deployment": "camera-stream-grpc",
                },
                "inspection-evaluator-grpc": {
                    "name": "Inspection Evaluator Service",
                    "endpoint": "inspection-evaluator-grpc:9090",
                    "namespace": None,
                    "deployment": "inspection-evaluator-grpc",
                },
            }
            self.environment = "compose"
        else:
            # Kubernetes環境用のサービス設定
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
                "inspection-evaluator-grpc-service": {
                    "name": "Inspection Evaluator Service",
                    "endpoint": "inspection-evaluator-grpc-service.image-processing.svc.cluster.local:9090",
                    "namespace": "image-processing",
                    "deployment": "inspection-evaluator-grpc-service",
                },
            }
            self.environment = "kubernetes"

        # Kubernetesクライアント初期化（Kubernetes環境でのみ実行）
        self.k8s_apps_v1 = None
        self.k8s_core_v1 = None

        # Kubernetes環境の場合のみKubernetesクライアントを初期化
        if self.environment == "kubernetes" and KUBERNETES_AVAILABLE:
            try:
                from kubernetes import config

                config.load_incluster_config()
                self.k8s_apps_v1 = k8s_client.AppsV1Api()
                self.k8s_core_v1 = k8s_client.CoreV1Api()
                logger.info("Kubernetes client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Kubernetes client: {e}")
        else:
            logger.info(
                f"Running in {self.environment} environment, skipping Kubernetes client initialization"
            )

    def _get_jst_time(self) -> str:
        """JST時刻を取得"""
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

    async def _get_pod_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """サービスのPod情報を取得"""
        if not self.k8s_core_v1:
            return None

        try:
            service_config = self.services.get(service_name)
            if not service_config:
                logger.warning(f"Service config not found for {service_name}")
                return None

            namespace = service_config["namespace"]
            deployment_name = service_config["deployment"]

            logger.debug(
                f"Getting pods for service {service_name} in namespace {namespace} with label app={deployment_name}"
            )

            # Podを取得
            pods = self.k8s_core_v1.list_namespaced_pod(
                namespace=namespace, label_selector=f"app={deployment_name}"
            )

            if pods.items:
                pod = pods.items[0]  # 最初のPodを取得
                return {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "restart_count": sum(
                        container.restart_count
                        for container in pod.status.container_statuses or []
                    ),
                    "created_time": (
                        pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        if pod.metadata.creation_timestamp
                        else "Unknown"
                    ),
                    "node_name": pod.spec.node_name or "Unknown",
                }
        except Exception as e:
            logger.error(
                f"Failed to get pod info for {service_name}: {e}", exc_info=True
            )

        return None

    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """指定されたgRPCサービスのヘルスチェックを実行"""
        start_time = time.time()

        try:
            service_config = self.services.get(service_name)
            if not service_config:
                return {
                    "status": "error",
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
                # gRPCヘルスチェックが利用可能な場合のみ実行
                if not GRPC_HEALTH_AVAILABLE:
                    logger.warning(
                        f"gRPC health check not available for {service_name}"
                    )
                    return {
                        "service_name": service_name,
                        "display_name": service_config["name"],
                        "status": "unknown",
                        "error": "gRPC health check library not available",
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "endpoint": endpoint,
                        "pod_info": None,
                        "last_checked": self._get_jst_time(),
                    }

                # 標準のgRPCヘルスチェックサービスを使用
                health_stub = health_pb2_grpc.HealthStub(channel)

                # 標準ヘルスチェックリクエストを作成
                health_request = health_pb2.HealthCheckRequest()
                # Empty service name for overall service health
                health_request.service = ""

                # タイムアウト付きでヘルスチェックを実行
                health_response = health_stub.Check(health_request, timeout=10.0)

                response_time_ms = (time.time() - start_time) * 1000

                # Pod情報を取得
                pod_info = await self._get_pod_info(service_name)

                # レスポンスのステータスを確認
                if health_response.status == health_pb2.HealthCheckResponse.SERVING:
                    return {
                        "service_name": service_name,
                        "display_name": service_config["name"],
                        "status": "healthy",
                        "response_time_ms": round(response_time_ms, 2),
                        "endpoint": endpoint,
                        "pod_info": pod_info,
                        "last_checked": self._get_jst_time(),
                    }
                else:
                    status_name = health_pb2.HealthCheckResponse.ServingStatus.Name(
                        health_response.status
                    )
                    pod_info = await self._get_pod_info(service_name)
                    return {
                        "service_name": service_name,
                        "display_name": service_config["name"],
                        "status": "unhealthy",
                        "response_time_ms": round(response_time_ms, 2),
                        "endpoint": endpoint,
                        "pod_info": pod_info,
                        "error": f"Service reported status: {status_name}",
                        "last_checked": self._get_jst_time(),
                    }

            except grpc.RpcError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_code = e.code()
                error_details = e.details()

                logger.error(
                    f"gRPC health check failed for {service_name}: {error_code} - {error_details}"
                )

                # Map gRPC error codes to appropriate statuses
                if error_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    status = "timeout"
                else:
                    status = "error"

                pod_info = await self._get_pod_info(service_name)
                return {
                    "service_name": service_name,
                    "display_name": service_config["name"],
                    "status": status,
                    "error": f"gRPC error: {error_code} - {error_details}",
                    "response_time_ms": round(response_time_ms, 2),
                    "endpoint": endpoint,
                    "pod_info": pod_info,
                    "last_checked": self._get_jst_time(),
                }

            finally:
                channel.close()

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Unexpected error during health check for {service_name}: {str(e)}"
            )
            pod_info = (
                await self._get_pod_info(service_name)
                if service_name in self.services
                else None
            )
            return {
                "service_name": service_name,
                "display_name": self.services.get(service_name, {}).get(
                    "name", service_name
                ),
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "response_time_ms": round(response_time_ms, 2),
                "pod_info": pod_info,
                "last_checked": self._get_jst_time(),
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
                        "last_checked": self._get_jst_time(),
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

        try:
            if self.environment == "kubernetes":
                return await self._restart_kubernetes_service(service_name)
            elif self.environment == "compose":
                return await self._restart_compose_service(service_name)
            elif self.environment == "nomad":
                return await self._restart_nomad_service(service_name)
            else:
                logger.error(
                    f"Unsupported environment for service restart: {self.environment}"
                )
                return False
        except Exception as e:
            logger.error(f"Unexpected error restarting service {service_name}: {e}")
            return False

    async def _restart_kubernetes_service(self, service_name: str) -> bool:
        """Kubernetes環境でのサービス再起動"""
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

            logger.info(f"Restarted Kubernetes service: {service_name}")
            return True

        except ApiException as e:
            logger.error(f"Failed to restart Kubernetes service {service_name}: {e}")
            return False

    async def _restart_compose_service(self, service_name: str) -> bool:
        """Docker Compose環境でのサービス再起動"""
        try:
            service_info = self.services[service_name]
            container_name = service_info["deployment"]

            # Docker Composeでサービスを再起動
            result = subprocess.run(
                ["docker", "compose", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info(f"Restarted Docker Compose service: {service_name}")
                return True
            else:
                logger.error(
                    f"Failed to restart Docker Compose service {service_name}: {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout restarting Docker Compose service {service_name}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to restart Docker Compose service {service_name}: {e}"
            )
            return False

    async def _restart_nomad_service(self, service_name: str) -> bool:
        """Nomad環境でのサービス再起動"""
        # Nomadでのサービス再起動は複雑なため、現在は未実装
        logger.warning(
            f"Service restart not implemented for Nomad environment: {service_name}"
        )
        return False

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

import asyncio
import json
import logging
import os
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ArgoWorkflowService:
    """Argo Workflows integration service for executing image processing pipelines"""

    def __init__(self):
        self.argo_server_url = os.getenv(
            "ARGO_SERVER_URL", "http://argo-server.argo.svc.cluster.local:2746"
        )
        self.namespace = os.getenv("ARGO_NAMESPACE", "argo")
        self.workflow_template = os.getenv(
            "WORKFLOW_TEMPLATE", "dynamic-image-processing"
        )
        self.timeout = int(os.getenv("ARGO_TIMEOUT", "300"))
        self.max_retries = int(os.getenv("ARGO_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("ARGO_RETRY_DELAY", "30"))
        self.argo_token = os.getenv(
            "ARGO_TOKEN", ""
        )  # Service account token for authentication
        self.insecure = (
            os.getenv("ARGO_INSECURE", "true").lower() == "true"
        )  # For dev environments

        # Configuration validation
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate Argo Workflows service configuration"""
        required_configs = {
            "argo_server_url": self.argo_server_url,
            "namespace": self.namespace,
            "workflow_template": self.workflow_template,
        }

        for config_name, config_value in required_configs.items():
            if not config_value:
                logger.error(f"Missing required configuration: {config_name}")
                raise ValueError(f"Missing required configuration: {config_name}")

        logger.info(f"Argo Workflows configuration validated:")
        logger.info(f"  Server URL: {self.argo_server_url}")
        logger.info(f"  Namespace: {self.namespace}")
        logger.info(f"  Workflow Template: {self.workflow_template}")
        logger.info(f"  Timeout: {self.timeout}s")
        logger.info(f"  Max Retries: {self.max_retries}")
        logger.info(f"  Retry Delay: {self.retry_delay}s")
        logger.info(f"  Insecure: {self.insecure}")
        logger.info(f"  Token configured: {'Yes' if self.argo_token else 'No'}")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Argo API requests"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.argo_token:
            headers["Authorization"] = f"Bearer {self.argo_token}"
        return headers

    async def health_check(self) -> bool:
        """Check if Argo Workflows server is accessible"""
        try:
            headers = self._get_headers()
            async with httpx.AsyncClient(
                timeout=10, verify=not self.insecure
            ) as client:
                response = await client.get(
                    f"{self.argo_server_url}/api/v1/info", headers=headers
                )
                if response.status_code == 200:
                    logger.info("Argo Workflows server is accessible")
                    return True
                elif response.status_code == 401:
                    logger.warning(
                        "Argo server authentication failed - token may be missing or invalid"
                    )
                    return False
                else:
                    logger.warning(
                        f"Argo server returned status {response.status_code}: {response.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Argo Workflows server health check failed: {e}")
            return False

    async def submit_pipeline_workflow(
        self,
        execution_id: str,
        pipeline_id: str,
        input_files: List[str],
        pipeline_definition: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Submit a pipeline workflow to Argo Workflows with retry logic

        Args:
            execution_id: Unique execution identifier
            pipeline_id: Pipeline definition identifier
            input_files: List of input file IDs/paths
            pipeline_definition: Pipeline configuration with components
            parameters: Additional execution parameters

        Returns:
            Workflow name if submitted successfully, None otherwise
        """
        logger.info(f"Attempting to submit workflow for execution {execution_id}")

        # First check if Argo server is accessible
        if not await self.health_check():
            logger.error(
                "Argo Workflows server is not accessible - cannot submit workflow"
            )
            return None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Workflow submission attempt {attempt + 1}/{self.max_retries} for execution {execution_id}"
                )

                workflow_name = (
                    f"pipeline-{execution_id}-{int(datetime.utcnow().timestamp())}"
                )

                # Build workflow payload
                workflow_payload = self._build_workflow_payload(
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                    pipeline_id=pipeline_id,
                    input_files=input_files,
                    pipeline_definition=pipeline_definition,
                    parameters=parameters or {},
                )

                logger.debug(
                    f"Workflow payload for {execution_id}: {json.dumps(workflow_payload, indent=2)}"
                )

                # Submit workflow via Argo Server API
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.argo_server_url}/api/v1/workflows/{self.namespace}",
                        json=workflow_payload,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code == 200:
                        workflow_response = response.json()
                        workflow_name_result = workflow_response.get(
                            "metadata", {}
                        ).get("name")
                        logger.info(
                            f"Successfully submitted workflow {workflow_name_result} for execution {execution_id}"
                        )
                        return workflow_name_result
                    else:
                        error_detail = response.text
                        logger.error(
                            f"Failed to submit workflow (attempt {attempt + 1}): {response.status_code} - {error_detail}"
                        )

                        # Don't retry on client errors (4xx)
                        if 400 <= response.status_code < 500:
                            logger.error(
                                f"Client error ({response.status_code}) - not retrying"
                            )
                            return None

                        # Only retry on server errors (5xx) or network issues
                        if attempt < self.max_retries - 1:
                            logger.info(f"Retrying in {self.retry_delay} seconds...")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            logger.error(
                                f"All {self.max_retries} attempts failed for execution {execution_id}"
                            )
                            return None

            except httpx.TimeoutException as e:
                logger.error(
                    f"Timeout submitting workflow (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts timed out for execution {execution_id}"
                    )
                    return None
            except Exception as e:
                logger.error(
                    f"Error submitting workflow (attempt {attempt + 1}) for execution {execution_id}: {e}"
                )
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed for execution {execution_id}"
                    )
                    return None

        return None

    async def get_workflow_status(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.argo_server_url}/api/v1/workflows/{self.namespace}/{workflow_name}"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get workflow status: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error getting workflow status for {workflow_name}: {e}")
            return None

    async def cancel_workflow(self, workflow_name: str) -> bool:
        """Cancel a running workflow"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.argo_server_url}/api/v1/workflows/{self.namespace}/{workflow_name}/terminate"
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"Error canceling workflow {workflow_name}: {e}")
            return False

    def _build_workflow_payload(
        self,
        workflow_name: str,
        execution_id: str,
        pipeline_id: str,
        input_files: List[str],
        pipeline_definition: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the workflow payload for Argo Workflows submission"""

        # Create workflow from template
        workflow_payload = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "generateName": f"{workflow_name}-",
                "namespace": self.namespace,
                "labels": {
                    "execution-id": execution_id,
                    "pipeline-id": pipeline_id,
                    "submitted-by": "imageflow-backend",
                },
            },
            "spec": {
                "workflowTemplateRef": {"name": self.workflow_template},
                "arguments": {
                    "parameters": [
                        {"name": "input-files", "value": json.dumps(input_files)},
                        {
                            "name": "pipeline-definition",
                            "value": json.dumps(pipeline_definition),
                        },
                        {"name": "execution-id", "value": execution_id},
                        {"name": "pipeline-id", "value": pipeline_id},
                    ]
                },
            },
        }

        # Add any additional parameters
        if parameters:
            workflow_payload["spec"]["arguments"]["parameters"].append(
                {"name": "additional-parameters", "value": json.dumps(parameters)}
            )

        return workflow_payload

    def _build_dynamic_workflow(
        self,
        workflow_name: str,
        execution_id: str,
        pipeline_definition: Dict[str, Any],
        input_files: List[str],
    ) -> Dict[str, Any]:
        """Build a dynamic workflow based on pipeline definition"""

        components = pipeline_definition.get("components", [])

        # Create DAG tasks based on components
        dag_tasks = []

        for i, component in enumerate(components):
            component_name = component.get("name", f"step-{i}")
            component_type = component.get("type")
            component_params = component.get("parameters", {})
            dependencies = component.get("dependencies", [])

            # Map component type to template
            template_mapping = {
                "resize": "resize-component",
                "ai_detection": "ai-detection-component",
                "object_detection": "ai-detection-component",
                "filter": "filter-component",
            }

            template_name = template_mapping.get(
                component_type, "generic-container-template"
            )

            task = {
                "name": f"{component_name}-task",
                "template": template_name,
                "arguments": {
                    "parameters": self._build_component_parameters(
                        component_type, component_params, i, workflow_name
                    )
                },
            }

            # Add dependencies
            if dependencies:
                task["dependencies"] = [f"{dep}-task" for dep in dependencies]
            elif i > 0:
                # If no explicit dependencies, depend on previous step
                prev_component = components[i - 1]
                task["dependencies"] = [
                    f"{prev_component.get('name', f'step-{i-1}')}-task"
                ]

            dag_tasks.append(task)

        # Build complete workflow
        workflow = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "name": workflow_name,
                "namespace": self.namespace,
                "labels": {
                    "execution-id": execution_id,
                    "submitted-by": "imageflow-backend",
                },
            },
            "spec": {
                "entrypoint": "main-pipeline",
                "arguments": {
                    "parameters": [
                        {"name": "input-files", "value": json.dumps(input_files)}
                    ]
                },
                "templates": [{"name": "main-pipeline", "dag": {"tasks": dag_tasks}}],
            },
        }

        return workflow

    def _build_component_parameters(
        self,
        component_type: str,
        component_params: Dict[str, Any],
        step_index: int,
        workflow_name: str,
    ) -> List[Dict[str, str]]:
        """Build parameters for a specific component"""

        base_params = [
            {
                "name": "input-path",
                "value": (
                    f"input/step-{step_index}"
                    if step_index == 0
                    else f"processed/step-{step_index-1}"
                ),
            },
            {
                "name": "output-path",
                "value": f"processed/{workflow_name}-step-{step_index}",
            },
        ]

        # Add component-specific parameters
        if component_type == "resize":
            base_params.extend(
                [
                    {"name": "width", "value": str(component_params.get("width", 800))},
                    {
                        "name": "height",
                        "value": str(component_params.get("height", 600)),
                    },
                    {
                        "name": "maintain-aspect",
                        "value": str(
                            component_params.get("maintain_aspect", True)
                        ).lower(),
                    },
                ]
            )
        elif component_type in ["ai_detection", "object_detection"]:
            base_params.extend(
                [
                    {"name": "model", "value": component_params.get("model", "yolo")},
                    {
                        "name": "confidence",
                        "value": str(component_params.get("confidence", 0.5)),
                    },
                    {
                        "name": "draw-boxes",
                        "value": str(component_params.get("draw_boxes", True)).lower(),
                    },
                    {
                        "name": "triton-url",
                        "value": "triton-service.default.svc.cluster.local:8000",
                    },
                ]
            )
        elif component_type == "filter":
            base_params.extend(
                [
                    {
                        "name": "filter-type",
                        "value": component_params.get("filter_type", "blur"),
                    },
                    {
                        "name": "intensity",
                        "value": str(component_params.get("intensity", 1.0)),
                    },
                ]
            )

        return base_params


# Global service instance
_argo_workflow_service = None


def get_argo_workflow_service() -> ArgoWorkflowService:
    """Get or create global ArgoWorkflowService instance"""
    global _argo_workflow_service
    if _argo_workflow_service is None:
        _argo_workflow_service = ArgoWorkflowService()
    return _argo_workflow_service

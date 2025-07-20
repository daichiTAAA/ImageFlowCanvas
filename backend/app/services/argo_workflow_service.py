"""
Legacy Argo Workflow Service - DEPRECATED
This service is now replaced by direct gRPC pipeline execution for 40-100ms performance
Kept as stub to avoid import errors during migration
"""
import logging

logger = logging.getLogger(__name__)

class ArgoWorkflowService:
    """
    DEPRECATED: Legacy Argo Workflow Service
    Replaced by GRPCPipelineExecutor for ultra-fast direct gRPC execution
    """
    
    def __init__(self):
        logger.warning("ArgoWorkflowService is deprecated. Use GRPCPipelineExecutor for direct gRPC calls.")
    
    async def submit_pipeline_workflow(self, **kwargs):
        """DEPRECATED: Use GRPCPipelineExecutor.execute_pipeline instead"""
        raise RuntimeError("Argo Workflows removed. Use direct gRPC pipeline execution.")
    
    async def get_workflow_status(self, workflow_name):
        """DEPRECATED: Workflow status monitoring is now handled by direct gRPC execution"""
        raise RuntimeError("Argo Workflows removed. Use direct gRPC pipeline execution.")
    
    async def health_check(self):
        """DEPRECATED: Use gRPC service health checks instead"""
        return False

# Global instance for backward compatibility
_argo_workflow_service_instance = None

def get_argo_workflow_service():
    """DEPRECATED: Returns stub instance. Use get_grpc_pipeline_executor() instead."""
    global _argo_workflow_service_instance
    if _argo_workflow_service_instance is None:
        _argo_workflow_service_instance = ArgoWorkflowService()
    return _argo_workflow_service_instance
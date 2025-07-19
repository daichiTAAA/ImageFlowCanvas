from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "ImageFlowCanvas API Server"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/health/argo")
async def argo_health_check():
    """Argo Workflowsサービスの健全性をチェック"""
    try:
        from app.services.argo_workflow_service import get_argo_workflow_service

        argo_service = get_argo_workflow_service()

        is_healthy = await argo_service.health_check()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "argo_server_url": argo_service.argo_server_url,
            "namespace": argo_service.namespace,
            "workflow_template": argo_service.workflow_template,
            "accessible": is_healthy,
        }
    except Exception as e:
        logger.error(f"Error checking Argo health: {e}")
        return {"status": "error", "error": str(e)}

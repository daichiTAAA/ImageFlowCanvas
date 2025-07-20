from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.services.auth_service import get_current_user
from app.services.grpc_monitor_service import GRPCMonitorService

router = APIRouter()
grpc_monitor = GRPCMonitorService()


@router.get("/health", response_model=List[Dict[str, Any]])
async def get_grpc_services_health(user=Depends(get_current_user)):
    """常駐gRPCサービスの健康状態を取得"""
    return await grpc_monitor.get_all_services_health()


@router.get("/{service_name}/health", response_model=Dict[str, Any])
async def get_service_health(service_name: str, user=Depends(get_current_user)):
    """特定のgRPCサービスの健康状態を取得"""
    health_status = await grpc_monitor.check_service_health(service_name)
    if health_status is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return health_status


@router.get("/", response_model=List[Dict[str, Any]])
async def get_grpc_services_info(user=Depends(get_current_user)):
    """常駐gRPCサービスの情報とメトリクスを取得"""
    return await grpc_monitor.get_services_info()


@router.post("/{service_name}/restart")
async def restart_grpc_service(service_name: str, user=Depends(get_current_user)):
    """gRPCサービスを再起動"""
    result = await grpc_monitor.restart_service(service_name)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to restart service")
    return {"message": f"Service {service_name} restart initiated"}

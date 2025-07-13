from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.services.auth_service import get_current_user
from app.services.component_service import ComponentService

router = APIRouter()
component_service = ComponentService()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_components(user=Depends(get_current_user)):
    """利用可能なコンポーネント一覧を取得"""
    return await component_service.get_available_components()

@router.get("/{component_id}", response_model=Dict[str, Any])
async def get_component(component_id: str, user=Depends(get_current_user)):
    """特定のコンポーネントの詳細を取得"""
    metadata = await component_service.get_component_metadata(component_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Component not found")
    return {
        "id": component_id,
        **metadata
    }

@router.post("/{component_id}/validate")
async def validate_component_parameters(
    component_id: str, 
    parameters: Dict[str, Any],
    user=Depends(get_current_user)
):
    """コンポーネントのパラメータを検証"""
    metadata = await component_service.get_component_metadata(component_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Component not found")
    
    validated_params = await component_service.validate_component_parameters(component_id, parameters)
    return {
        "component_id": component_id,
        "validated_parameters": validated_params,
        "metadata": metadata
    }
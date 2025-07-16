from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pipeline import Pipeline, PipelineCreateRequest, PipelineUpdateRequest
from app.services.pipeline_service import PipelineService
from app.services.auth_service import get_current_user
from app.database import get_db

router = APIRouter()
pipeline_service = PipelineService()


@router.get("/", response_model=List[Pipeline])
async def get_pipelines(
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """パイプライン一覧を取得"""
    return await pipeline_service.get_all_pipelines(db)


@router.post("/", response_model=Pipeline)
async def create_pipeline(
    pipeline_request: PipelineCreateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新しいパイプラインを作成"""
    return await pipeline_service.create_pipeline(pipeline_request, db)


@router.get("/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(
    pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """特定のパイプラインを取得"""
    pipeline = await pipeline_service.get_pipeline(pipeline_id, db)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.put("/{pipeline_id}", response_model=Pipeline)
async def update_pipeline(
    pipeline_id: str,
    pipeline_request: PipelineUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """パイプラインを更新"""
    pipeline = await pipeline_service.update_pipeline(pipeline_id, pipeline_request, db)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """パイプラインを削除"""
    success = await pipeline_service.delete_pipeline(pipeline_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"message": "Pipeline deleted successfully"}

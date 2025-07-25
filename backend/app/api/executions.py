from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from typing import List, Optional
from app.models.execution import Execution, ExecutionRequest, ExecutionStatus
from app.services.execution_service import get_global_execution_service
from app.services.auth_service import get_current_user

router = APIRouter()
execution_service = get_global_execution_service()


@router.post("/", response_model=dict)
async def execute_pipeline(
    pipeline_id: str = Form(...),
    priority: str = Form("normal"),
    input_files: List[UploadFile] = File(...),
    parameters: Optional[str] = Form("{}"),
    user=Depends(get_current_user),
):
    """パイプラインを実行"""
    import json

    try:
        params = json.loads(parameters) if parameters else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid parameters JSON")

    execution_request = ExecutionRequest(
        pipeline_id=pipeline_id, parameters=params, priority=priority
    )

    execution = await execution_service.execute_pipeline(execution_request, input_files)
    return {
        "execution_id": execution.execution_id,
        "status": execution.status,
        "estimated_completion": None,  # 実装時に計算
    }


@router.get("/{execution_id}", response_model=Execution)
async def get_execution_status(execution_id: str, user=Depends(get_current_user)):
    """実行状況を取得"""
    execution = await execution_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/", response_model=List[Execution])
async def get_executions(
    limit: int = 100, offset: int = 0, pipeline_id: Optional[str] = None, user=Depends(get_current_user)
):
    """実行履歴を取得（パイプラインIDでフィルタ可能）"""
    return await execution_service.get_executions(limit, offset, pipeline_id)


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str, user=Depends(get_current_user)):
    """実行をキャンセル"""
    success = await execution_service.cancel_execution(execution_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Execution not found or cannot be cancelled"
        )
    return {"message": "Execution cancelled successfully"}


@router.post("/{execution_id}/fix-timestamps")
async def fix_execution_timestamps(execution_id: str, user=Depends(get_current_user)):
    """実行のタイムスタンプを修正（デバッグ用）"""
    success = await execution_service.fix_execution_timestamps(execution_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Execution not found or could not fix timestamps"
        )
    return {"message": "Timestamps fixed successfully"}

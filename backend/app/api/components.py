from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from app.services.auth_service import get_current_user

router = APIRouter()

# 利用可能なコンポーネントの定義
AVAILABLE_COMPONENTS = [
    {
        "id": "resize",
        "name": "画像リサイズ",
        "description": "画像のサイズを変更します",
        "parameters": {
            "width": {"type": "integer", "default": 800, "description": "幅（ピクセル）"},
            "height": {"type": "integer", "default": 600, "description": "高さ（ピクセル）"},
            "maintain_aspect": {"type": "boolean", "default": True, "description": "アスペクト比を維持"}
        },
        "input_types": ["image/jpeg", "image/png", "image/tiff"],
        "output_types": ["image/jpeg", "image/png"]
    },
    {
        "id": "ai_detection",
        "name": "AI物体検出",
        "description": "画像内の物体を検出します",
        "parameters": {
            "model": {"type": "string", "default": "yolo11", "options": ["yolo11"], "description": "使用するAIモデル"},
            "confidence": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0, "description": "検出信頼度の閾値"},
            "draw_boxes": {"type": "boolean", "default": True, "description": "検出結果を画像に描画"}
        },
        "input_types": ["image/jpeg", "image/png"],
        "output_types": ["image/jpeg", "image/png"]
    },
    {
        "id": "filter",
        "name": "画像フィルタ",
        "description": "画像にフィルタ効果を適用します",
        "parameters": {
            "filter_type": {"type": "string", "default": "blur", "options": ["blur", "sharpen", "edge", "emboss"], "description": "フィルタの種類"},
            "intensity": {"type": "float", "default": 1.0, "min": 0.0, "max": 5.0, "description": "フィルタの強度"}
        },
        "input_types": ["image/jpeg", "image/png"],
        "output_types": ["image/jpeg", "image/png"]
    },
    {
        "id": "enhancement",
        "name": "画像補正",
        "description": "画像の明度、コントラスト等を調整します",
        "parameters": {
            "brightness": {"type": "float", "default": 1.0, "min": 0.0, "max": 2.0, "description": "明度調整"},
            "contrast": {"type": "float", "default": 1.0, "min": 0.0, "max": 2.0, "description": "コントラスト調整"},
            "saturation": {"type": "float", "default": 1.0, "min": 0.0, "max": 2.0, "description": "彩度調整"}
        },
        "input_types": ["image/jpeg", "image/png"],
        "output_types": ["image/jpeg", "image/png"]
    }
]

@router.get("/", response_model=List[Dict[str, Any]])
async def get_components(user=Depends(get_current_user)):
    """利用可能なコンポーネント一覧を取得"""
    return AVAILABLE_COMPONENTS

@router.get("/{component_id}", response_model=Dict[str, Any])
async def get_component(component_id: str, user=Depends(get_current_user)):
    """特定のコンポーネントの詳細を取得"""
    component = next((c for c in AVAILABLE_COMPONENTS if c["id"] == component_id), None)
    if not component:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Component not found")
    return component
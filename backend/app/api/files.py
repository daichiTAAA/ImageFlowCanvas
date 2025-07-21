from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from app.services.file_service import FileService
from app.services.auth_service import get_current_user
from typing import Optional, List

router = APIRouter()
file_service = FileService()


@router.post("/")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    """ファイルをアップロード"""
    try:
        file_id = await file_service.upload_file(file)
        return {
            "file_id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}/download")
async def download_file_direct(file_id: str, user=Depends(get_current_user)):
    """ファイルを直接ダウンロード（ブラウザ表示用）"""
    try:
        file_stream, filename, content_type = await file_service.download_file(file_id)
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}")
async def download_file(file_id: str, user=Depends(get_current_user)):
    """ファイルをダウンロード"""
    try:
        file_stream, filename, content_type = await file_service.download_file(file_id)
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_file(file_id: str, user=Depends(get_current_user)):
    """ファイルを削除"""
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_files(
    prefix: Optional[str] = Query(None, description="ファイル名のプレフィックス"),
    extension: Optional[str] = Query(
        None, description="ファイル拡張子フィルタ (.json, .jpg など)"
    ),
    user=Depends(get_current_user),
):
    """ファイル一覧を取得"""
    try:
        files = await file_service.list_files(
            prefix=prefix or "", file_extension=extension
        )
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}/preview")
async def preview_json_file(file_id: str, user=Depends(get_current_user)):
    """JSONファイルの内容をプレビュー"""
    try:
        # Get file info to check if it's a JSON file
        file_stream, filename, content_type = await file_service.download_file(file_id)
        
        # Check if file is JSON by filename or content type
        is_json = (filename.lower().endswith(".json") or 
                   content_type == "application/json")
        
        if not is_json:
            raise HTTPException(
                status_code=400, detail="Only JSON files can be previewed"
            )

        # Read content and parse JSON
        content = file_stream.read().decode('utf-8')
        import json
        json_content = json.loads(content)
        
        return json_content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON content")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import asyncio
import json
import logging
from app.api import pipelines, executions, components, files, auth
from app.services.websocket_manager import ConnectionManager
from app.services.execution_worker import execution_worker
from app.database import init_db

# ログ設定を早期に初期化
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Argo Workflows関連のログレベルを調整
logging.getLogger("app.services.argo_workflow_service").setLevel(logging.INFO)
logging.getLogger("app.services.execution_worker").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # HTTP リクエストのログを抑制

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ImageFlowCanvas API",
    description="Dynamic image processing pipeline API",
    version="1.0.0",
)


# データベース初期化
@app.on_event("startup")
async def startup_event():
    logger.info("Starting ImageFlowCanvas API...")
    await init_db()
    logger.info("Database initialized")


# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket接続マネージャー
manager = ConnectionManager()


# カスタムCORSミドルウェア（リダイレクト時にもCORSヘッダーを追加）
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)

    # すべてのレスポンスにCORSヘッダーを追加
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
    )
    response.headers["Access-Control-Expose-Headers"] = "Content-Length,Content-Range"

    return response


# APIルーターの登録
app.include_router(auth.router, prefix="/v1/auth", tags=["authentication"])
app.include_router(pipelines.router, prefix="/v1/pipelines", tags=["pipelines"])
app.include_router(executions.router, prefix="/v1/executions", tags=["executions"])
app.include_router(components.router, prefix="/v1/components", tags=["components"])
app.include_router(files.router, prefix="/v1/files", tags=["files"])


@app.websocket("/v1/ws/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket)
    # 特定の実行IDの進捗更新を購読
    manager.subscribe_to_execution(execution_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # クライアントからのメッセージを処理
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    await manager.send_personal_json({"type": "pong"}, websocket)
                elif message_type == "auth":
                    # 認証メッセージの処理
                    token = message.get("token")
                    if token:
                        await manager.send_personal_json(
                            {
                                "type": "auth_success",
                                "message": "Authentication successful",
                            },
                            websocket,
                        )
                    else:
                        await manager.send_personal_json(
                            {"type": "auth_error", "message": "Authentication failed"},
                            websocket,
                        )
                elif message_type == "watch":
                    # 監視開始メッセージの処理
                    execution_id_watch = message.get("executionId")
                    if execution_id_watch:
                        manager.subscribe_to_execution(execution_id_watch, websocket)
                        await manager.send_personal_json(
                            {
                                "type": "watch_started",
                                "executionId": execution_id_watch,
                            },
                            websocket,
                        )
                    else:
                        await manager.send_personal_json(
                            {"type": "error", "message": "Invalid execution ID"},
                            websocket,
                        )
                else:
                    await manager.send_personal_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        },
                        websocket,
                    )
            except json.JSONDecodeError:
                await manager.send_personal_json(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        manager.unsubscribe_from_execution(execution_id, websocket)
        manager.disconnect(websocket)


@app.websocket("/v1/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # クライアントからのメッセージを処理
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    await manager.send_personal_json({"type": "pong"}, websocket)
                elif message_type == "auth":
                    # 認証メッセージの処理
                    token = message.get("token")
                    if token:
                        await manager.send_personal_json(
                            {
                                "type": "auth_success",
                                "message": "Authentication successful",
                            },
                            websocket,
                        )
                    else:
                        await manager.send_personal_json(
                            {"type": "auth_error", "message": "Authentication failed"},
                            websocket,
                        )
                elif message_type == "watch":
                    # 監視開始メッセージの処理
                    execution_id_watch = message.get("executionId")
                    if execution_id_watch:
                        manager.subscribe_to_execution(execution_id_watch, websocket)
                        await manager.send_personal_json(
                            {
                                "type": "watch_started",
                                "executionId": execution_id_watch,
                            },
                            websocket,
                        )
                    else:
                        await manager.send_personal_json(
                            {"type": "error", "message": "Invalid execution ID"},
                            websocket,
                        )
                else:
                    await manager.send_personal_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        },
                        websocket,
                    )
            except json.JSONDecodeError:
                await manager.send_personal_json(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"message": "ImageFlowCanvas API Server"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/argo")
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
            "accessible": is_healthy
        }
    except Exception as e:
        logger.error(f"Error checking Argo health: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にワーカーを開始"""
    logger.info("Starting execution worker...")
    try:
        # Argo Workflowsサービスの初期化状況をチェック
        from app.services.argo_workflow_service import get_argo_workflow_service
        argo_service = get_argo_workflow_service()
        logger.info("Argo Workflows service initialized")
        
        # バックグラウンドタスクとしてワーカーを起動
        asyncio.create_task(execution_worker.start())
        logger.info("Execution worker started successfully")
    except Exception as e:
        logger.error(f"Error starting worker: {e}")
        # ワーカー開始失敗でもサーバーは起動を続ける


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時にワーカーを停止"""
    logger.info("Stopping execution worker...")
    await execution_worker.stop()
    logger.info("Execution worker stopped")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

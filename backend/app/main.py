from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import asyncio
import json
from app.api import pipelines, executions, components, files, auth
from app.services.websocket_manager import ConnectionManager
from app.services.execution_worker import execution_worker
from app.database import init_db

app = FastAPI(
    title="ImageFlowCanvas API",
    description="Dynamic image processing pipeline API",
    version="1.0.0",
)


# データベース初期化
@app.on_event("startup")
async def startup_event():
    await init_db()


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
            except json.JSONDecodeError:
                await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.unsubscribe_from_execution(execution_id, websocket)
        manager.disconnect(websocket)


@app.websocket("/v1/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # メッセージ処理ロジックをここに実装
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"message": "ImageFlowCanvas API Server"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にワーカーを開始"""
    print("Starting execution worker...")
    try:
        # バックグラウンドタスクとしてワーカーを起動
        asyncio.create_task(execution_worker.start())
    except Exception as e:
        print(f"Error starting worker: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時にワーカーを停止"""
    print("Stopping execution worker...")
    await execution_worker.stop()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

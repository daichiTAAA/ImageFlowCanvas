from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import asyncio
import logging
from app.api import (
    pipelines,
    executions,
    components,
    files,
    auth,
    websocket,
    health,
    products,
    grpc_services,
    camera_stream,
    inspection_masters,
    inspection_execution,
)
from app.services.execution_worker import execution_worker
from app.database import init_db
from app.services.websocket_manager import ConnectionManager

# ログ設定を早期に初期化
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

# gRPC services関連のログレベルを調整
logging.getLogger("app.services.grpc_pipeline_executor").setLevel(logging.INFO)
logging.getLogger("app.services.execution_worker").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # HTTP リクエストのログを抑制

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ImageFlowCanvas API",
    description="Dynamic image processing pipeline API",
    version="1.0.0",
)

# WebSocketマネージャーのグローバルインスタンス
manager = ConnectionManager()


# データベース初期化
@app.on_event("startup")
async def init_database():
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
app.include_router(health.router, prefix="/v1", tags=["health"])
# Camera stream router must be registered BEFORE general websocket router to avoid path conflicts
app.include_router(camera_stream.router, prefix="/v1", tags=["camera-stream"])
app.include_router(websocket.router, prefix="/v1", tags=["websocket"])
app.include_router(auth.router, prefix="/v1/auth", tags=["authentication"])
app.include_router(pipelines.router, prefix="/v1/pipelines", tags=["pipelines"])
app.include_router(executions.router, prefix="/v1/executions", tags=["executions"])
app.include_router(components.router, prefix="/v1/components", tags=["components"])
app.include_router(files.router, prefix="/v1/files", tags=["files"])
# Products API aligned with others: mount under /v1/products
app.include_router(products.router, prefix="/v1/products", tags=["products"])
# Mirror under /api/v1/products for KMP client default base URL
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(
    grpc_services.router, prefix="/v1/grpc-services", tags=["grpc-services"]
)
# Inspection APIs
app.include_router(
    inspection_masters.router, prefix="/v1/inspection", tags=["inspection"]
)
app.include_router(
    inspection_execution.router, prefix="/v1/inspection", tags=["inspection"]
)
# Health monitoring endpoints (no auth required)
app.include_router(grpc_services.router, prefix="/v1/monitoring", tags=["monitoring"])


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にワーカーを開始"""
    logger.info("Starting execution worker...")
    try:
        # gRPC pipeline executor の初期化状況をチェック
        from app.services.grpc_pipeline_executor import get_grpc_pipeline_executor

        grpc_executor = get_grpc_pipeline_executor()
        logger.info("gRPC pipeline executor initialized")

        # バックグラウンドタスクとしてワーカーを起動
        asyncio.create_task(execution_worker.start())
        logger.info("Execution worker started successfully with direct gRPC execution")
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

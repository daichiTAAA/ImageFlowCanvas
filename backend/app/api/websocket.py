from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging
from app.services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket接続マネージャー（シングルトンパターンで管理）
_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


@router.websocket("/ws/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    manager = get_manager()
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


@router.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    manager = get_manager()
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

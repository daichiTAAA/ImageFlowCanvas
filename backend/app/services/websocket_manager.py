from typing import List, Dict
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.execution_subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """WebSocket接続を受け入れ"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """WebSocket接続を切断"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 実行IDの購読からも削除
        for execution_id, connections in self.execution_subscriptions.items():
            if websocket in connections:
                connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """特定のWebSocketに個人メッセージを送信"""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def send_personal_json(self, data: dict, websocket: WebSocket):
        """特定のWebSocketにJSONメッセージを送信"""
        try:
            await websocket.send_text(json.dumps(data))
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """全ての接続にメッセージをブロードキャスト"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # 切断された接続を削除
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_json(self, data: dict):
        """全ての接続にJSONメッセージをブロードキャスト"""
        await self.broadcast(json.dumps(data))

    def subscribe_to_execution(self, execution_id: str, websocket: WebSocket):
        """特定の実行IDに対する進捗更新を購読"""
        if execution_id not in self.execution_subscriptions:
            self.execution_subscriptions[execution_id] = []
        if websocket not in self.execution_subscriptions[execution_id]:
            self.execution_subscriptions[execution_id].append(websocket)

    def unsubscribe_from_execution(self, execution_id: str, websocket: WebSocket):
        """特定の実行IDの購読を解除"""
        if execution_id in self.execution_subscriptions:
            if websocket in self.execution_subscriptions[execution_id]:
                self.execution_subscriptions[execution_id].remove(websocket)

    async def send_execution_update(self, execution_id: str, update_data: dict):
        """特定の実行IDの購読者に更新を送信"""
        if execution_id in self.execution_subscriptions:
            message = {
                "type": "progress",
                "execution_id": execution_id,
                "data": update_data,
            }
            disconnected = []
            for websocket in self.execution_subscriptions[execution_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)

            # 切断された接続を削除
            for websocket in disconnected:
                self.unsubscribe_from_execution(execution_id, websocket)

    async def broadcast_execution_update(self, execution_id: str, update_data: dict):
        """実行更新を購読者と全体にブロードキャスト"""
        # 特定の実行IDの購読者に送信
        await self.send_execution_update(execution_id, update_data)

        # 全体にもブロードキャスト（実行リスト画面などの更新用）
        message = {
            "type": "execution_update",
            "execution_id": execution_id,
            "data": update_data,
        }
        await self.broadcast_json(message)

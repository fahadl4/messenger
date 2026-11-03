
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Connections for users viewing specific rooms.
        self.room_connections: dict[int, set[WebSocket]] = defaultdict(set)

        # Connections for users receiving sidebar notifications.
        self.user_connections: dict[int, set[WebSocket]] = defaultdict(set)

    # -------- ROOM CONNECTIONS --------

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.room_connections[room_id].add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        connections = self.room_connections.get(room_id)

        if connections is not None:
            connections.discard(websocket)

            if not connections:
                self.room_connections.pop(room_id, None)

    async def broadcast(self, room_id: int, message: dict):
        connections = list(self.room_connections.get(room_id, set()))

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(room_id, websocket)

    # -------- USER NOTIFICATIONS --------

    async def connect_user(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.user_connections[user_id].add(websocket)

    def disconnect_user(self, user_id: int, websocket: WebSocket):
        connections = self.user_connections.get(user_id)

        if connections is not None:
            connections.discard(websocket)

            if not connections:
                self.user_connections.pop(user_id, None)

    async def notify_user(self, user_id: int, notification: dict):
        connections = list(self.user_connections.get(user_id, set()))

        for websocket in connections:
            try:
                await websocket.send_json(notification)
            except Exception:
                self.disconnect_user(user_id, websocket)


manager = ConnectionManager()

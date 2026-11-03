
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.websocket_manager import manager
from app.core.security import get_user_from_token
from app.db.database_connection import AsyncSessionLocal
from app.models.chat_room import ChatRoom
from app.models.chat_room_members import ChatRoomMember
from app.crud.message import save_message
from app.crud.chat_room_members import get_all_members

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/notifications")
async def user_notifications_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_from_token(token, db)

        if user is None:
            await websocket.close(code=1008)
            return

        user_id = user.id

    await manager.connect_user(user_id, websocket)

    try:
        while True:
            # Keep the connection alive while the user is logged in.
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_user(user_id, websocket)

@router.websocket("/ws/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: int,
):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_from_token(token, db)

        if user is None:
            await websocket.close(code=1008)
            return

        result = await db.execute(
            select(ChatRoomMember)
            .join(
                ChatRoom,
                ChatRoom.id == ChatRoomMember.room_id,
            )
            .where(
                ChatRoomMember.room_id == room_id,
                ChatRoomMember.user_id == user.id,
                ChatRoomMember.left_at.is_(None),
                ChatRoom.deleted_at.is_(None),
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            await websocket.close(code=1008)
            return

    await manager.connect(room_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if not isinstance(data, dict):
                await websocket.send_json({
                    "error": "Message must be a JSON object"
                })
                continue

            content = data.get("content")

            if not isinstance(content, str) or not content.strip():
                await websocket.send_json({
                    "error": "Message content cannot be empty"
                })
                continue

            content = content.strip()

            if len(content) > 5000:
                await websocket.send_json({
                    "error": "Message cannot exceed 5000 characters"
                })
                continue

            # Open a database session to save this message.
            async with AsyncSessionLocal() as db:
                # Save the message using the shared CRUD function.
                new_message = await save_message(
                    db=db,
                    room_id=room_id,
                    user_id=user.id,
                    content=content,
                )

                # Format the saved message for WebSocket clients.
                message_data = {
                    "id": new_message.id,
                    "room_id": new_message.room_id,
                    "sender_id": new_message.sender_id,
                    "content": new_message.content,
                    "created_at": new_message.created_at.isoformat(),
                    "updated_at": new_message.updated_at.isoformat(),
                    "deleted_for_everyone_at": (
                        new_message.deleted_for_everyone_at.isoformat()
                        if new_message.deleted_for_everyone_at
                        else None
                    ),
                }
            
            # Broadcast the actual message to users viewing this room.
            await manager.broadcast(room_id, message_data)

            # Notify all active room members so their sidebars can update.
            async with AsyncSessionLocal() as db:
                members = await get_all_members(db, room_id)

                for member in members:
                    if member.left_at is None:
                        await manager.notify_user(
                            member.user_id,
                            {
                                "type": "new_message",
                                "room_id": room_id,
                                "message": message_data,
                            },
                        )


    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
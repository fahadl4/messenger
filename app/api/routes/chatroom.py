from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.crud.chat_room_members import delete_member
from app.crud.chatroom import create_chat_room, create_group_chat, get_all_chat_rooms
from app.db.database_connection import get_db
from app.models.user import User
from app.schemas.chatroom import ChatRoomCreate, ChatRoomDelete, ChatRoomListResponse, ChatRoomResponse, GroupChatCreate

router = APIRouter(
    prefix="/chatroom",
    tags=["Chat Room"],
)

@router.post("", response_model=ChatRoomResponse)
async def create_room(room_data: ChatRoomCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await create_chat_room(db, current_user.id, room_data)

@router.post("/group", response_model=ChatRoomResponse)
async def create_group(
    group_data: GroupChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_group_chat(
        db,
        current_user.id,
        group_data,
    )

@router.get("", response_model=list[ChatRoomListResponse])
async def get_rooms(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_chat_rooms(db, current_user.id)

@router.delete("/delete")
async def delete_chat_room(
    data: ChatRoomDelete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await delete_member(
        db,
        data.room_id,
        current_user.id
    )
    
    '''await check_and_delete_room(
        db,
        data.room_id,
    )'''

    await db.commit()

    return {
        "message": "Chat deleted successfully"
    }
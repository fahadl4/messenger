from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

#from app.models.chat_room import ChatRoom
from app.models.chat_room_members import ChatRoomMember


async def get_member(db: AsyncSession, room_id: int, user_id: int):
    result = await db.execute(
        select(ChatRoomMember).where(
            ChatRoomMember.room_id == room_id,
            ChatRoomMember.user_id == user_id,
            ChatRoomMember.left_at.is_(None),
        )
    )
    return result.scalar_one_or_none()

async def get_all_members(db: AsyncSession, room_id: int):
    members = await db.execute(select(ChatRoomMember).where(ChatRoomMember.room_id == room_id))
    return members.scalars().all()

async def add_member(db: AsyncSession, room_id: int, user_id: int):
    existing_member = await get_member(
        db,
        room_id,
        user_id
    )
    if existing_member is not None:
        if existing_member.left_at is None:
            raise HTTPException(
                status_code=400,
                detail="User is already a member of this group.",
            )

        # Reactivate the existing membership.
        existing_member.left_at = None
        return existing_member
    
    member = ChatRoomMember(
        room_id = room_id,
        user_id = user_id
    )
    
    db.add(member)
    return member

async def delete_member(db: AsyncSession, room_id: int, user_id: int):
    member = await get_member(db, room_id, user_id)
    
    if member is None:
        raise HTTPException(
            status_code=404,
            detail="Chatroom membership not found."
        )
    now = datetime.now(timezone.utc)
    
    member.left_at = now
    member.messages_deleted_at = now
    
    return member


async def reactivate_member(db: AsyncSession, room_id: int, user_id: int):
    result = await db.execute(
        select(ChatRoomMember).where(
            ChatRoomMember.room_id == room_id,
            ChatRoomMember.user_id == user_id,
        )
    )

    member = result.scalar_one_or_none()

    if member is not None and member.left_at is not None:
        member.left_at = None

    return member

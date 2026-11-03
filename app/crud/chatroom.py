from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.chat_room_members import add_member
from app.models.chat_room import ChatRoom
from app.models.chat_room_members import ChatRoomMember
from app.models.message import Message
from app.models.user import User
from app.schemas.chatroom import ChatRoomCreate, GroupChatCreate


async def create_chat_room(
    db: AsyncSession,
    user_id: int,
    room_data: ChatRoomCreate
):
    if user_id == room_data.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot create a chat room with yourself"
        )

    # Find an existing room shared by these two users,
    # including memberships that have been deactivated.
    result = await db.execute(
        select(ChatRoom)
        .join(
            ChatRoomMember,
            ChatRoomMember.room_id == ChatRoom.id
        )
        .where(
            ChatRoomMember.user_id.in_(
                [user_id, room_data.receiver_id]
            )
        )
        .group_by(ChatRoom.id)
        .having(
            func.count(func.distinct(ChatRoomMember.user_id)) == 2
        )
    )

    existing_room = result.scalars().first()

    if existing_room is not None:
        # Reactivate only the person sending this request.
        member_result = await db.execute(
            select(ChatRoomMember).where(
                ChatRoomMember.room_id == existing_room.id,
                ChatRoomMember.user_id == user_id,
            )
        )
        sender_member = member_result.scalar_one_or_none()

        if sender_member is not None and sender_member.left_at is not None:
            sender_member.left_at = None

        await db.commit()
        await db.refresh(existing_room)
        return existing_room

    # No shared room exists, so create one.
    room = ChatRoom(created_by=user_id)
    db.add(room)
    await db.flush()

    await add_member(db, room.id, user_id)
    await add_member(db, room.id, room_data.receiver_id)

    await db.commit()
    await db.refresh(room)

    return room

async def create_group_chat(db: AsyncSession, user_id: int, group_data: GroupChatCreate):
    # Remove duplicate IDs and the creator's ID.
    members_id = set(group_data.member_ids)
    members_id.discard(user_id)
    
    if not members_id:
        raise HTTPException(
            status_code=400,
            detail="A group must have at least one other member."
        )
    # Check that every selected user exists and is active.
    result = await db.execute(select(User.id).where(User.id.in_(members_id), User.deleted_at.is_(None)))
    existing_user_ids = set(result.scalars().all())
    
    if existing_user_ids != members_id:
        raise HTTPException(
            status_code=400,
            detail="One or more selected users do not exist or are inactive.",
        )
    room = ChatRoom(
        created_by = user_id,
        name = group_data.name.strip(),
        is_group = True
    )
    if not room.name:
        raise HTTPException(
            status_code=400,
            detail="Group name cannot be empty.",
        )
    db.add(room)
    await db.flush()
    
    await add_member(db, room.id, user_id)
    
    for member_id in members_id:
        await add_member(db, room.id, member_id)
    
    await db.commit()
    await db.refresh(room)

    return room
    

async def get_all_chat_rooms(db: AsyncSession, user_id: int):
    last_message_query = (
        select(
            Message.room_id.label("room_id"),
            Message.content.label("last_message"),
            Message.created_at.label("last_message_at"),
            Message.deleted_for_everyone_at.label("last_message_deleted_at"),
        )
        .distinct(Message.room_id)
        .order_by(
            Message.room_id,
            Message.created_at.desc(),
            Message.id.desc(),
        )
        .subquery()
    )

    # Details of the other participant in private chats.
    other_member = (
        select(
            ChatRoomMember.room_id.label("room_id"),
            User.id.label("other_user_id"),
            User.name.label("other_user_name"),
            User.email.label("other_user_email"),
            User.avatar_url.label("other_user_avatar_url"),
        )
        .join(User, User.id == ChatRoomMember.user_id)
        .where(
            ChatRoomMember.user_id != user_id,
            ChatRoomMember.left_at.is_(None),
            ChatRoomMember.room_id.in_(
                select(ChatRoom.id).where(ChatRoom.is_group.is_(False))
            ),
        )
        .subquery()
    )

    # Count active members in each room.
    member_counts = (
        select(
            ChatRoomMember.room_id.label("room_id"),
            func.count(ChatRoomMember.user_id).label("member_count"),
        )
        .where(ChatRoomMember.left_at.is_(None))
        .group_by(ChatRoomMember.room_id)
        .subquery()
    )

    result = await db.execute(
        select(
            ChatRoom.id.label("id"),
            ChatRoom.created_by.label("created_by"),
            ChatRoom.created_at.label("created_at"),
            ChatRoom.name.label("name"),
            ChatRoom.is_group.label("is_group"),
            other_member.c.other_user_id,
            other_member.c.other_user_name,
            other_member.c.other_user_email,
            other_member.c.other_user_avatar_url,
            func.coalesce(member_counts.c.member_count, 0).label("member_count"),
            last_message_query.c.last_message,
            last_message_query.c.last_message_at,
            last_message_query.c.last_message_deleted_at,
        )
        .join(
            ChatRoomMember,
            ChatRoomMember.room_id == ChatRoom.id,
        )
        .outerjoin(
            other_member,
            other_member.c.room_id == ChatRoom.id,
        )
        .outerjoin(
            member_counts,
            member_counts.c.room_id == ChatRoom.id,
        )
        .outerjoin(
            last_message_query,
            last_message_query.c.room_id == ChatRoom.id,
        )
        .where(
            ChatRoomMember.user_id == user_id,
            ChatRoomMember.left_at.is_(None),
            ChatRoom.deleted_at.is_(None),
        )
        .order_by(
            last_message_query.c.last_message_at.desc().nullslast(),
            ChatRoom.updated_at.desc(),
        )
    )

    return [
        {
            "id": row.id,
            "created_by": row.created_by,
            "created_at": row.created_at,
            "name": row.name,
            "is_group": row.is_group,
            "other_user_id": row.other_user_id,
            "other_user_name": row.other_user_name,
            "other_user_email": row.other_user_email,
            "other_user_avatar_url": row.other_user_avatar_url,
            "member_count": row.member_count,
            "last_message": (
                "This message was deleted"
                if row.last_message_deleted_at is not None
                else row.last_message
            ),
            "last_message_at": row.last_message_at,
        }
        for row in result
    ]

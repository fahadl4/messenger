from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.chat_room_members import (
    get_member,
    get_all_members,
    reactivate_member,
)
from app.models.chat_room_members import ChatRoomMember
from app.models.message import Message
from app.models.message_deletion import MessageDeletion
from app.models.user import User
from app.schemas.message import MessageContent, MessageCreate, MessageDelete, MessageUpdate


async def save_message(
    db: AsyncSession,
    room_id: int,
    user_id: int,
    content: str,
):
    content = content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Message content cannot be empty."
        )

    if len(content) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Message cannot exceed 5000 characters."
        )

    message = Message(
        room_id=room_id,
        sender_id=user_id,
        content=content,
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message



async def create_Message(
    db: AsyncSession,
    user_id: int,
    message_data: MessageContent
):
    # Reactivate the sender if they previously deleted this conversation.
    sender_member = await reactivate_member(
        db,
        message_data.room_id,
        user_id
    )

    if sender_member is None:
        raise HTTPException(
            status_code=403,
            detail="You aren't a member of this room."
        )

    # Reactivate other participants so the conversation can reappear.
    members = await get_all_members(db, message_data.room_id)

    for member in members:
        if member.user_id != user_id and member.left_at is not None:
            member.left_at = None

    # Save the message using the shared helper.
    message = await save_message(
        db=db,
        room_id=message_data.room_id,
        user_id=user_id,
        content=message_data.content
    )

    return message


async def getMessages(db: AsyncSession, user_id: int, room_id: int):
    member = await get_member(
        db,
        room_id,
        user_id
    )
    if member is None:
        raise HTTPException(
            status_code=403,
            detail="You aren't a member of this room."
        )
        
    query = select(Message).where(
    Message.room_id == room_id,

    # Not deleted for everyone
    #Message.deleted_for_everyone_at.is_(None),

    # Not deleted for this user
    ~exists().where(
        MessageDeletion.message_id == Message.id,
        MessageDeletion.user_id == user_id
    )
)

    if member.messages_deleted_at is not None:
        query = query.where(
            Message.created_at > member.messages_deleted_at
        )

    query = query.order_by(
        Message.created_at
    )
    
    dataList = await db.execute(query)
    messages = dataList.scalars().all()
    
    return messages

async def get_meeting_messages(
    db: AsyncSession,
    user_id: int,
    room_id: int,
):
    # Check that the current user belongs to this room.
    member = await get_member(db, room_id, user_id)

    if member is None:
        raise HTTPException(
            status_code=403,
            detail="You aren't a member of this room."
        )
    
    members_result = await db.execute(
    select(User.id, User.name)
    .join(
        ChatRoomMember,
        ChatRoomMember.user_id == User.id,
    )
    .where(
        ChatRoomMember.room_id == room_id,
        ChatRoomMember.left_at.is_(None),
    )
)

    room_members = {
        user_id: name
        for user_id, name in members_result.all()
    }

    # Only include messages from the last 24 hours.
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

    query = (
        select(Message, User.name)
        .join(User, User.id == Message.sender_id)
        .where(
            Message.room_id == room_id,
            Message.created_at >= cutoff_time,

            # Exclude messages deleted for everyone.
            Message.deleted_for_everyone_at.is_(None),

            # Exclude messages deleted for this user.
            ~exists().where(
                MessageDeletion.message_id == Message.id,
                MessageDeletion.user_id == user_id,
            ),
        )
    )

    # Respect this user's deleted conversation history.
    if member.messages_deleted_at is not None:
        query = query.where(
            Message.created_at > member.messages_deleted_at
        )

    query = query.order_by(Message.created_at)

    result = await db.execute(query)

    return result.all(), room_members

async def updateMessage(db: AsyncSession, user_id: int, message_data: MessageUpdate):
    result = await db.execute(select(Message).where(Message.id == message_data.message_id))
    message = result.scalar_one_or_none()
    
    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Mesage does not exist"
        )
    member = await get_member(
        db,
        message.room_id,
        user_id
    )
    if member is None:
        raise HTTPException(
            status_code=403,
            detail="You are not the member of this room."
        )
    if message.sender_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own messages"
        )
    if message.deleted_for_everyone_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Deleted messages cannot be edited"
        )
    
    message.content = message_data.content
    await db.commit()
    await db.refresh(message)
    return message

async def deleteMessageForMe(db: AsyncSession, user_id: int, message_data: MessageDelete):
    for message_id in message_data.message_ids:
        result = await db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()
            
        if message is None:
            raise HTTPException(
                status_code=404,
                detail="Message does not exist"
            )
                
        member = await get_member(
            db,
            message.room_id,
            user_id
        )
        if member is None:
            raise HTTPException(
                status_code=403,
                detail="You are not the member of this room."
            )
        messageDeletion = await db.execute(select(MessageDeletion).where(MessageDeletion.message_id == message.id, MessageDeletion.user_id == user_id))
        existing_deletion = messageDeletion.scalar_one_or_none()
        
        if existing_deletion is not None:
            raise HTTPException(
                status_code=400,
                detail="Message is already deleted for you"
            )
        
        deletion = MessageDeletion(
            message_id = message.id,
            user_id = user_id
        )
        db.add(deletion)
    await db.commit()
    return {
            "message": "Messages deleted for me"
        }
    
    

async def deleteMessageForEveryone(db: AsyncSession, user_id: int, message_data: MessageDelete):
    for message_id in message_data.message_ids:
        result = await db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()
        
        if message is None:
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found"
            )
            
        member = await get_member(
            db,
            message.room_id,
            user_id
        )
        
        if member is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this chat room"
            )
        
        if message.sender_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own messages for everyone"
            )
        
        message.deleted_for_everyone_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {
        "message": "Messages deleted for everyone"
    }
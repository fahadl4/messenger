from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.crud.message import create_Message, deleteMessageForEveryone, deleteMessageForMe, getMessages, get_meeting_messages, updateMessage
from app.db.database_connection import get_db
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageContent, MessageCreate, MessageDelete, MessageResponse, MessageUpdate
from app.core.ai_service import analyze_meeting
from app.schemas.meeting import MeetingAnalysisRequest


router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

@router.post("", response_model = MessageResponse)
async def send_message(message_data: MessageContent, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await create_Message(db, current_user.id, message_data) 

@router.post("/getMessages", response_model= list[MessageResponse])
async def get_messages(message_data: MessageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await getMessages(db, current_user.id, message_data.room_id)

@router.patch("", response_model=MessageResponse)
async def message_update(message_data: MessageUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await updateMessage(db, current_user.id, message_data)

@router.delete("/deleteForMe")
async def delete_for_me(message_data: MessageDelete, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await deleteMessageForMe(db, current_user.id, message_data)

@router.delete("/delete")
async def delete_message(message_data: MessageDelete, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await deleteMessageForEveryone(db, current_user.id, message_data)


@router.post("/analyze-meeting")
async def analyze_chat_meeting(
    request: MeetingAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, room_members = await get_meeting_messages(
        db,
        current_user.id,
        request.room_id,
    )

    conversation = "\n".join(
        f"{sender_name}: {message.content}"
        for message, sender_name in rows
    )

    if not conversation.strip():
        return {
            "meeting_agreed": False,
            "title": None,
            "date": None,
            "time": None,
            "duration_minutes": None,
            "participants": [],
            "participant_responses": [],
            "needs_clarification": True,
            "clarification_question": (
                "There are no visible messages from the last 24 hours to analyze."
            ),
        }

    print("CONVERSATION SENT TO AI:")
    print(conversation)
    result = await analyze_meeting(conversation)

    # Only accept participants who are active members of this room.
    valid_names = set(room_members.values())

    valid_responses = [
        participant
        for participant in result["participant_responses"]
        if participant["name"] in valid_names
    ]

    result["participant_responses"] = valid_responses

    # Only include actual members who explicitly agreed.
    agreed_names = list(dict.fromkeys(
        participant["name"]
        for participant in valid_responses
        if participant["response"] == "agreed"
    ))

    result["participants"] = agreed_names

    if len(agreed_names) < 2:
        result["meeting_agreed"] = False
        result["needs_clarification"] = True
        result["clarification_question"] = (
            "At least two actual group members must agree to the meeting."
        )

    return result
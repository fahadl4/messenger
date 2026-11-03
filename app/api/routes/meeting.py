
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.ai_service import analyze_meeting
from app.db.database_connection import get_db
from app.crud.message import get_meeting_messages
from app.crud.meeting import create_meeting, get_meeting_participants, get_my_meetings
from app.models.user import User
from app.schemas.meeting import MeetingAnalysisRequest


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post("/analyze")
async def analyze_and_create_meeting(
    request: MeetingAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages, room_members = await get_meeting_messages(
        db=db,
        user_id=current_user.id,
        room_id=request.room_id,
    )

    if not messages:
        raise HTTPException(
            status_code=400,
            detail="No messages available for meeting analysis.",
        )

    conversation_lines = []

    for message, sender_name in messages:
        conversation_lines.append(
            f"[User ID: {message.sender_id}] "
            f"{sender_name}: {message.content}"
        )

    conversation = "\n".join(conversation_lines)

    try:
        ai_result = await analyze_meeting(conversation)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Meeting analysis returned invalid data.",
        ) from exc

    meeting = await create_meeting(
        db=db,
        room_id=request.room_id,
        ai_result=ai_result,
        room_members=room_members,
    )

    if meeting is None:
        return {
            "message": "No agreed meeting could be created.",
            "analysis": ai_result,
        }

    return {
        "message": "Meeting created successfully.",
        "meeting": {
            "id": meeting.id,
            "room_id": meeting.room_id,
            "proposed_by": meeting.proposed_by,
            "title": meeting.title,
            "meeting_date": meeting.meeting_date.astimezone(
                ZoneInfo("Asia/Karachi")
            ).isoformat(),
            "duration_minutes": meeting.duration_minutes,
        },
    }

@router.get("/my-meetings")
async def read_my_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meetings = await get_my_meetings(
        db=db,
        user_id=current_user.id,
    )

    meeting_list = []

    for meeting in meetings:
        participants = await get_meeting_participants(
            db=db,
            meeting_id=meeting.id,
        )

        # Include the proposer even if they are not in Meeting_Participant.
        proposer = await db.get(User, meeting.proposed_by)

        if proposer and not any(
            p["user_id"] == proposer.id for p in participants
        ):
            participants.insert(
                0,
                {
                    "user_id": proposer.id,
                    "name": proposer.name.strip(),
                },
            )

        meeting_list.append(
            {
                "id": meeting.id,
                "room_id": meeting.room_id,
                "title": meeting.title,
                "proposed_by": meeting.proposed_by,
                "meeting_date": meeting.meeting_date.astimezone(
                    ZoneInfo("Asia/Karachi")
                ).isoformat(),
                "duration_minutes": meeting.duration_minutes,
                "participants": participants,
            }
        )

    return {"meetings": meeting_list}

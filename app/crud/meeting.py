from datetime import datetime
from fastapi import HTTPException
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.chat_room_members import get_member
from app.models.meeting import Meeting
from app.models.meeting_participant import Meeting_Participant
from app.models.user import User

async def get_meeting_by_details(db: AsyncSession, room_id: int, proposed_by: int, title: str, meeting_date: datetime):
    result = await db.execute(select(Meeting).where(
        Meeting.room_id == room_id,
        Meeting.proposed_by == proposed_by,
        Meeting.title == title,
        Meeting.meeting_date == meeting_date
    ))
    existing_meeting = result.scalar_one_or_none()
    
    return existing_meeting

async def get_meeting_participants(db: AsyncSession, meeting_id: int):
    query = (select(User.id, User.name).join(
        Meeting_Participant, User.id == Meeting_Participant.participant_id
    ).where(
        Meeting_Participant.meeting_id == meeting_id
    ))
    
    result = await db.execute(query)
    rows = result.all()
    
    participants = [{"user_id":user_id, "name":name.strip()} for user_id, name in rows]
    return participants

async def get_my_meetings(db: AsyncSession, user_id: int):
    now = datetime.now(ZoneInfo("Asia/Karachi"))

    query = (
        select(Meeting)
        .outerjoin(
            Meeting_Participant,
            Meeting.id == Meeting_Participant.meeting_id,
        )
        .where(
            or_(
                Meeting.proposed_by == user_id,
                Meeting_Participant.participant_id == user_id,
            ),
            Meeting.meeting_date >= now,
        )
        .distinct()
        .order_by(Meeting.meeting_date.asc())
    )

    result = await db.execute(query)

    return result.scalars().all()

async def sync_meeting_participants(
    db: AsyncSession,
    meeting_id: int,
    room_id: int,
    participants: list[dict],
    room_members: dict[int, str],
):
    if not isinstance(participants, list):
        raise HTTPException(
            status_code=400,
            detail="Invalid participants list.",
        )

    if not isinstance(room_members, dict) or not room_members:
        raise HTTPException(
            status_code=400,
            detail="Invalid room members.",
        )
    
    # Validate the room member mapping.
    if not all(
        isinstance(user_id, int)
        and not isinstance(user_id, bool)
        and user_id > 0
        and isinstance(name, str)
        and name.strip()
        for user_id, name in room_members.items()
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid room member IDs or names.",
        )

    # Extract participant IDs directly.
    desired_ids = set()

    for participant in participants:
        if not isinstance(participant, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid participant data.",
            )

        user_id = participant.get("user_id")

        if (
            not isinstance(user_id, int)
            or isinstance(user_id, bool)
            or user_id not in room_members
        ):
            raise HTTPException(
                status_code=400,
                detail="A participant is not an active room member.",
            )

        desired_ids.add(user_id)

    # Retrieve existing participant records.
    result = await db.execute(
        select(Meeting_Participant).where(
            Meeting_Participant.meeting_id == meeting_id
        )
    )

    existing_records = result.scalars().all()

    existing_ids = {
        record.participant_id
        for record in existing_records
    }

    # Remove participants no longer in the agreed list.
    remove_ids = existing_ids - desired_ids

    for record in existing_records:
        if record.participant_id in remove_ids:
            await db.delete(record)

    # Add newly agreed participants.
    add_ids = desired_ids - existing_ids

    for user_id in add_ids:
        db.add(
            Meeting_Participant(
                meeting_id=meeting_id,
                participant_id=user_id,
            )
        )

    await db.flush()
    
async def create_meeting(
    db: AsyncSession,
    room_id: int,
    ai_result: dict,
    room_members: dict[int, str],
):
    if not isinstance(ai_result, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid AI meeting result.",
        )

    meeting_agreed = ai_result.get("meeting_agreed")

    if not isinstance(meeting_agreed, bool):
        raise HTTPException(
            status_code=400,
            detail="Invalid meeting agreement value!",
        )

    if not meeting_agreed:
        return None

    title = ai_result.get("title")
    date = ai_result.get("date")
    time = ai_result.get("time")
    duration_minutes = ai_result.get("duration_minutes")
    proposed_by_id = ai_result.get("proposed_by_user_id")
    participants = ai_result.get("participants")

    # Validate the proposer ID.
    if (
        not isinstance(proposed_by_id, int)
        or isinstance(proposed_by_id, bool)
        or proposed_by_id not in room_members
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid meeting proposer.",
        )

    # Validate the participant list.
    if not isinstance(participants, list):
        raise HTTPException(
            status_code=400,
            detail="Invalid participants list.",
        )

    participant_ids = set()

    for participant in participants:
        if not isinstance(participant, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid participant data.",
            )

        participant_id = participant.get("user_id")

        if (
            not isinstance(participant_id, int)
            or isinstance(participant_id, bool)
            or participant_id not in room_members
        ):
            raise HTTPException(
                status_code=400,
                detail="A participant is not an active room member.",
            )

        participant_ids.add(participant_id)

    # At least two distinct people must agree.
    if len(participant_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two distinct participants must agree.",
        )

    if not isinstance(title, str) or not title.strip():
        return None

    if not isinstance(date, str) or not isinstance(time, str):
        raise HTTPException(
            status_code=400,
            detail="Meeting date and time are required.",
        )

    if duration_minutes is not None:
        if (
            not isinstance(duration_minutes, int)
            or isinstance(duration_minutes, bool)
            or duration_minutes <= 0
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid meeting duration.",
            )

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time, "%H:%M").time()

        meeting_date = datetime.combine(
            date_obj,
            time_obj,
            tzinfo=ZoneInfo("Asia/Karachi"),
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date and time!",
        )

    now = datetime.now(ZoneInfo("Asia/Karachi"))

    if meeting_date < now:
        raise HTTPException(
            status_code=400,
            detail="Meeting date cannot be in the past!",
        )

    try:
        existing_meeting = await get_meeting_by_details(
            db,
            room_id,
            proposed_by_id,
            title.strip(),
            meeting_date,
        )

        if existing_meeting:
            meeting = existing_meeting
            meeting_id = existing_meeting.id
        else:
            meeting = Meeting(
                room_id=room_id,
                proposed_by=proposed_by_id,
                title=title.strip(),
                meeting_date=meeting_date,
                duration_minutes=duration_minutes,
            )

            db.add(meeting)
            await db.flush()
            meeting_id = meeting.id

        await sync_meeting_participants(
            db,
            meeting_id,
            room_id,
            participants,
            room_members,
        )

        await db.commit()
        return meeting

    except Exception:
        await db.rollback()
        raise

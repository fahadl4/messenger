from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_connection import Base


class Meeting_Participant(Base):
    __tablename__ = "meeting_participants"
    
    id: Mapped[int] = mapped_column(
        primary_key = True,
        index = True
    )
    
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id"),
        nullable = False
    )
    
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable = False
    )
    
    __table_args__ = (
        Index(
            "uq_meeting_participant",
            "meeting_id",
            "participant_id",
            unique=True,
        ),
    )
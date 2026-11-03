from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_connection import Base


class Meeting(Base):
    __tablename__ = "meetings"
    
    id: Mapped[int] = mapped_column(
        primary_key = True,
        index = True
    )
    
    room_id: Mapped[int] = mapped_column(
        ForeignKey("chat_rooms.id"),
        nullable = False
    )
    
    proposed_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable = False
    )
    
    title: Mapped[str] = mapped_column(
        String(100),
        nullable = False
    )
    
    meeting_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable = False
    )
    
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable = True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable = False,
        server_default = func.now()
    )
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, func,Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_connection import Base

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )
    
    room_id: Mapped[int] = mapped_column(
        ForeignKey("chat_rooms.id"),
        nullable=False
    )

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
        
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    deleted_for_everyone_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
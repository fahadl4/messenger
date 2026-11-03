from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_connection import Base

class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )
    
    room_id: Mapped[int] = mapped_column(
        ForeignKey("chat_rooms.id"),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    
    joined_at: Mapped[datetime] = mapped_column(
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
            
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    messages_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    __table_args__ = (
        Index(
            "uq_active_room_user",
            "room_id",
            "user_id",
            unique=True,
            postgresql_where=text("left_at IS NULL")
        ),
    )
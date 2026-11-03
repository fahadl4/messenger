from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_connection import Base

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )
    
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    is_group: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )
    
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
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
        
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    
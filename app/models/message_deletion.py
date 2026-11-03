from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database_connection import Base


class MessageDeletion(Base):
    __tablename__ = "message_deletions"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
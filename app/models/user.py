import enum
from datetime import datetime
from sqlalchemy import String, DateTime, func, text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM

from app.db.database_connection import Base

class UserStatus(enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    role: Mapped[UserStatus] = mapped_column(
        ENUM(UserStatus, name="user_status", values_callable=lambda enum_class: [item.value for item in enum_class]),
        default=UserStatus.USER,
        server_default="user",
        nullable=False
    )
    
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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
    
    __table_args__ = (
        Index(
            "uq_active_user_email",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL")
        ),
    )
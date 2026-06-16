from __future__ import annotations
from datetime import datetime, UTC

from sqlalchemy import String, Integer, Boolean, DateTime, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.config import settings


class User(Base) :
    __tablename__ = 'users'

    id            : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username      : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email         : Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash : Mapped[str] = mapped_column(String(100), nullable=False)
    is_superuser  : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_path    : Mapped[str | None] = mapped_column(String(200), default=None)
    last_login    : Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at     : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = lambda : datetime.now(UTC),
        server_default = text("now()"),
        nullable = False
    )

    created_tasks : Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys = "[Task.creator_id]",
        back_populates="creator",
    ) 
    owned_tasks : Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="[Task.owner_id]",
        back_populates="owner"
        
    )
    workspaces : Mapped[list["Workspace"]] = relationship(  
        secondary="workspace_member",
        back_populates="members",
        viewonly=True,
    )
    reset_tokens : Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @property
    def get_image_path(self):
        if not self.image_path:
            # return "/static/defaults/default_profile_picture.jpg"
            return f"https://{settings.s3_bucket_name}.s3.{settings.s3_region}.amazonaws.com/profile_pics/{self.image_path}"
        return f"/media/profile_pics/{self.image_path}"


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id    : Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash : Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # storing the hash is more secure, malicious actor cannot do anything with just the hash
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="reset_tokens")
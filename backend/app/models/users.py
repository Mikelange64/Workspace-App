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
    password_hash : Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified   : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_superuser  : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_premium    : Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_file    : Mapped[str | None] = mapped_column(String(200), default=None)
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
        passive_deletes=True,
    )
    owned_tasks : Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="[Task.owner_id]",
        back_populates="owner",
        passive_deletes=True,
    )
    workspaces : Mapped[list["Workspace"]] = relationship(  
        secondary="workspace_member",
        back_populates="members",
        viewonly=True,
    )
    reset_tokens : Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens : Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    verification_tokens : Mapped[list["VerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    folders : Mapped[list["Folder"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    # Conversations/messages are workspace data, not personal data - they
    # outlive their creator/sender. creator_id/sender_id get nulled out at
    # the DB level (ON DELETE SET NULL) instead of cascading, so no ORM
    # cascade here; passive_deletes lets Postgres handle rows not loaded
    # in the current session too.
    conversations_created : Mapped[list["Conversation"]] = relationship(
        back_populates="creator", passive_deletes=True
    )
    messages_sent : Mapped[list["Message"]] = relationship(
        back_populates="sender", passive_deletes=True
    )

    @property
    def image_path(self):
        if self.image_file:
            return f"https://{settings.s3_bucket_name}.s3.{settings.s3_region}.amazonaws.com/profile_pics/{self.image_file}"
        return "/static/defaults/default_profile_picture.jpg"


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


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id    : Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash : Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id         : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id    : Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash : Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at : Mapped[datetime] = mapped_column(  
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="verification_tokens")
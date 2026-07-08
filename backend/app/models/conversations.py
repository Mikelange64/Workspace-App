from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import Integer, Text, ForeignKey, DateTime, String, Boolean, Enum as sqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConversationType(str, Enum):
    WORKSPACE = "WORKSPACE"
    BOT = "BOT"


class Conversation(Base):
    __tablename__ = "conversations"

    id           : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type         : Mapped[ConversationType] = mapped_column(sqlEnum(ConversationType), nullable=False)
    workspace_id : Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True
    )
    creator_id   : Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    title        : Mapped[str] = mapped_column(String(100), nullable=False)
    created_at   : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    is_pinned    : Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived  : Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", foreign_keys=[workspace_id], back_populates="conversations"
    )
    creator : Mapped["User | None"] = relationship(
        "User", foreign_keys=[creator_id], back_populates="conversations_created"
    )

    @property
    def last_message_at(self):
        if self.messages :
            last_message = self.messages[-1]
            return last_message.created_at


class Message(Base):
    __tablename__ = "messages"

    id              : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id : Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("conversations.id"), 
        nullable=False, 
        index=True
    ) 
    sender_id : Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    content    : Mapped[str] = mapped_column(Text, nullable=False)
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    conversation : Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages",
    )
    sender : Mapped["User | None"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="messages_sent"
    )
    
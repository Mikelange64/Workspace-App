from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import Integer, Text, ForeignKey, DateTime, String, Boolean, JSON, Enum as sqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConversationType(str, Enum):
    WORKSPACE = "WORKSPACE"
    BOT = "BOT"

class SenderType(Enum):
    USER = "USER"
    BOT  = "BOT"


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
    last_opened_at  : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    # Null until the first message is sent - set by the send_message endpoint,
    # not defaulted at creation time (a new conversation has no messages yet).
    last_message_at : Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    messages     : Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    workspace    : Mapped["Workspace"] = relationship(
        "Workspace", foreign_keys=[workspace_id], back_populates="conversations"
    )
    creator      : Mapped["User | None"] = relationship(
        "User", foreign_keys=[creator_id], back_populates="conversations_created"
    )

    @property
    def last_message(self) -> str | None:
        if not self.messages:
            return None
        content = self.messages[-1].content
        return content if len(content) <= 100 else content[:100] + "…"


class Message(Base):
    __tablename__ = "messages"

    id              : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id : Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("conversations.id"), 
        nullable=False, 
        index=True
    ) 
    sender_id       : Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    sender_type     : Mapped[SenderType] = mapped_column(sqlEnum(SenderType), nullable=False)
    content         : Mapped[str] = mapped_column(Text, nullable=False)
    # List of {"title", "url"} dicts from the web_search tool, in the order
    # they were found - null for messages that never triggered a search.
    sources         : Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=None)
    created_at      : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    conversation    : Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages",
    )
    sender          : Mapped["User | None"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="messages_sent"
    )
    
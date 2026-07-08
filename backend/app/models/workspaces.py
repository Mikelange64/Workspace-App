from datetime import UTC, datetime, timedelta
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id          : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Historical record only - the creator has no special privileges beyond
    # having been the first admin, so this survives its creator's account
    # deletion instead of blocking it or taking the workspace down with them.
    creator_id  : Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title       : Mapped[str] = mapped_column(String(50), nullable=False)
    description : Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    max_number  : Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    folder_id   : Mapped[int | None] = mapped_column(Integer, ForeignKey("folders.id"), nullable=True, default=None, index=True)

    folder: Mapped["Folder | None"] = relationship(back_populates="workspaces")
    members: Mapped[list["User"]] = relationship(
        secondary="workspace_member", back_populates="workspaces", viewonly=True
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="workspace", cascade="all, delete-orphan"
    )
    conversations : Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="workspace", cascade="all, delete-orphan"
    )

    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    is_pinned     : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived   : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_completed  : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at  : Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @property
    def default_due_date(self) -> datetime | None:
        dates = [t.due_date for t in self.tasks if t.due_date is not None]
        return max(dates) if dates else None

    @property
    def num_of_members(self) -> int:
        return len(self.members)

    @property
    def num_of_tasks(self) -> int:
        return len(self.tasks)

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0

        completed = [t for t in self.tasks if t.is_completed]
        return (len(completed) / len(self.tasks)) * 100

    @property
    def time_remaining(self) -> timedelta | None:
        if self.due_date is None:
            return None

        return self.due_date - datetime.now(UTC)


class Folder(Base):
    __tablename__ = "folders"

    id         : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id   : Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name       : Mapped[str] = mapped_column(String(50), nullable=False)
    color      : Mapped[str] = mapped_column(String(50), nullable=False)
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    owner      : Mapped["User"] = relationship(back_populates="folders")
    workspaces : Mapped[list["Workspace"]] = relationship(back_populates="folder")
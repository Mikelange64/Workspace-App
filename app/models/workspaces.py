from datetime import UTC, datetime, timedelta

from sqlalchemy import (
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_number: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    members: Mapped[list["User"]] = relationship(
        secondary="workspace_member", back_populates="workspaces", viewonly=True
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="workspace", cascade="all, delete-orphan"
    )

    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

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

        return self.due_date - datetime.now()

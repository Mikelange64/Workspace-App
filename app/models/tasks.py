from __future__ import annotations

from datetime import datetime, UTC
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base) :
    __tablename__ = "task"

    id           : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title        : Mapped[str] = mapped_column(String(50), nullable=False)
    content      : Mapped[str] = mapped_column(Text, nullable=False)
    is_completed : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_public    : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creator_id   : Mapped[int] = mapped_column(
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        index=True
    )
    workspace_id : Mapped[int] = mapped_column(
        Integer,
        ForeignKey('workspace.id'),
        nullable=True,
        index=True
    )

    creator : Mapped["User"] = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    workspace : Mapped["Workspace"] = relationship("Workspace", foreign_keys=[workspace_id], back_populates="tasks")

    date_created : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = lambda : datetime.now(UTC)
    )
    due_date   : Mapped[datetime] = mapped_column( DateTime(timezone=True), nullable=True )

    @property
    def _days_remaining(self):
        if self.due_date is None:
            return None
        return (self.due_date - self.date_created).days
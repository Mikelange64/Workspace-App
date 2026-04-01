from __future__ import annotations

from datetime import datetime, UTC
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


user_workspace = Table(
    "user_workspace",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("workspace_id", Integer, ForeignKey("workspace.id"), primary_key=True),
)


class Workspace(Base):
    __tablename__ = "workspace"

    id          : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title       : Mapped[str] = mapped_column(String(50), nullable=False)
    description : Mapped[str] = mapped_column(Text, nullable=False)
    max_number  : Mapped[int] = mapped_column(Integer, default=None)

    members : Mapped[list["User"]] = relationship(
        secondary="user_workspace",
        back_populates="workspaces"
    )
    tasks   : Mapped[list["Task"]] = relationship("Task", back_populates="workspace", cascade="all, delete-orphan")

    date_created : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = lambda : datetime.now(UTC),
    )
    due_date : Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @property
    def default_due_date(self):
        dates = [t.due_date for t in self.tasks if t.due_date is not None]
        return max(dates) if dates else None
from datetime import datetime, UTC
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workspace(Base):
    __tablename__ = "workspace"

    id          : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_id  : Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title       : Mapped[str] = mapped_column(String(50), nullable=False)
    description : Mapped[str] = mapped_column(Text, nullable=False)
    max_number  : Mapped[int] = mapped_column(Integer, default=None)

    members : Mapped[list["User"]] = relationship(
        secondary="workspace_member",
        back_populates="workspaces",
        viewonly=True
    )
    tasks   : Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )

    date_created : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = lambda : datetime.now(UTC),
    )
    due_date : Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None)

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

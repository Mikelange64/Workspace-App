from datetime import UTC, datetime

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


class Task(Base):
    __tablename__ = "tasks"

    id           : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title        : Mapped[str] = mapped_column(String(50), nullable=False)
    content      : Mapped[str] = mapped_column(Text, nullable=False)
    is_completed : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creator_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("workspaces.id"), 
        nullable=False, 
        index=True
    )
    
    date_created : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    due_date     : Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[creator_id], back_populates="created_tasks"
    )
    owner: Mapped["User"]          = relationship(
        "User", foreign_keys=[owner_id], back_populates="owned_tasks"
    )
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", foreign_keys=[workspace_id], back_populates="tasks"
    )

    @property
    def _days_remaining(self):
        if self.due_date is None:
            return None
        return (self.due_date - self.date_created).days

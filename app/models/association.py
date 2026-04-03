from datetime import datetime, UTC

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, mapped_column, Mapped

from app.database import Base


class WorkspaceMember(Base):
    __tablename__ = 'workspace_member'

    id           : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id      : Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), primary_key=True)
    workspace_id : Mapped[int] = mapped_column(Integer, ForeignKey('workspace.id'), primary_key=True)
    role         : Mapped[str] = mapped_column(String(50), nullable=False, default="member")

    joined_at    : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )
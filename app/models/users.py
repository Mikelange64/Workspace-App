from __future__ import annotations
from datetime import datetime, UTC

from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base) :
    __tablename__ = 'user'

    id            : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username      : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email         : Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash : Mapped[str] = mapped_column(String(100), nullable=False)
    is_superuser  : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_path    : Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    created_tasks : Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="creator",
    )
    workspaces : Mapped[list["Workspace"]] = relationship(
        secondary="workspace_member",
        back_populates="members",
        viewonly=True,
    )

    @property
    def get_image_path(self):
        if not self.image_path:
            return "/static/defaults/default_profile_picture.jpg"
        return f"/media/profile_pics/{self.image_path}"
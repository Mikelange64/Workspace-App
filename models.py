from datetime import datetime, UTC
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base) :
    __tablename__ = 'user'

    id : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash : Mapped[str] = mapped_column(String(50), nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(50), nullable=False, default=None)

    notes: Mapped[list[Reminder]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    @property
    def get_image_path(self):
        if not self.image_path:
            return "/static/defaults/default_profile_picture.jpg"
        return self.image_path


class Reminder(Base) :
    __tablename__ = "reminder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title : Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status : Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        index=True
    )

    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = lambda : datetime.now(UTC)
    )

    due_date : Mapped[datetime] = mapped_column( DateTime(timezone=True), nullable=True)
    owner : Mapped[User] = relationship(back_poulates="notes")

    @property
    def _days_remaining(self):
        return (self.due_date - self.date_posted ).days


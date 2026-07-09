import re

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum as sqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import datetime, UTC
from enum import Enum

from app.database import Base
from app.config import settings

class ResourceType(str, Enum):
    LINK = "LINK"
    FILE = "FILE"
    NOTE = "NOTE"


class Resource(Base):
    __tablename__ = "resources"

    id           : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id      : Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    created_by   : Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    type         : Mapped[ResourceType] = mapped_column(sqlEnum(ResourceType), nullable=False)
    title        : Mapped[str] = mapped_column(String(100), nullable=False)
    file_key     : Mapped[str | None] = mapped_column(String)
    url          : Mapped[str | None] = mapped_column(String)
    content      : Mapped[str | None] = mapped_column(Text)
    mime_type    : Mapped[str | None] = mapped_column(String)
    thumbnail_url: Mapped[str | None] = mapped_column(String)
    created_at   : Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default= lambda : datetime.now(UTC)
    )
    task : Mapped["Task"] = relationship(
        "Task", foreign_keys=[task_id], back_populates="resources"
    )

    @property
    def file_path(self) -> str | None :
        if not self.file_key:
            return None
    
        # Deferred import avoids a models -> utils -> models circular import
        # (app.utils.__init__ pulls in queries.py, which imports app.models).
        from app.utils.image_utils import _get_s3_client
    
        # Force download instead of inline rendering: without this, opening
        # the URL directly serves the object with whatever Content-Type it
        # was uploaded with, and a browser will render it in place rather
        # than downloading it. Strip CR/LF/quotes from the filename first -
        # it's client-controlled (the original upload filename) and gets
        # embedded in a response header.
        safe_title = re.sub(r'[\r\n"]', "_", self.title)
    
        return _get_s3_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": f"files/{self.file_key}",
                "ResponseContentDisposition": f'attachment; filename="{safe_title}"',
            },
            ExpiresIn=900,  # 15 minutes - regenerated fresh on every authorized request
        )

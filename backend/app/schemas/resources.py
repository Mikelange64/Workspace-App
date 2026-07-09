from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from datetime import datetime


class ResourceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id         : int
    task_id    : int
    title      : str
    created_at : datetime


# =============================================== LINKS ======================================================

class LinkCreate(BaseModel):
    title : str = Field(min_length=1, max_length=100)
    url   : HttpUrl


class LinkResponse(ResourceBase):
    url           : HttpUrl
    thumbnail_url : str | None = None


class LinkUpdate(BaseModel):
    title : str | None = Field(default=None, min_length=1, max_length=100)
    url   : HttpUrl | None = None

# =============================================== NOTES ======================================================

class NoteCreate(BaseModel):
    title   : str = Field(min_length=1, max_length=100)
    content : str = Field(max_length=100000)


class NoteResponse(ResourceBase):
    content : str


class NoteUpdate(BaseModel):
    title    : str | None = Field(default=None, min_length=1, max_length=100)
    content  : str | None = Field(default=None, min_length=1, max_length=100000)

# =============================================== FILES ======================================================

class FileResponse(ResourceBase):
    file_path : str | None
    mime_type : str

# =============================================== MIXED LIST =================================================

class ResourceSummary(ResourceBase):
    type          : str
    url           : HttpUrl | None = None
    content       : str | None = None
    file_path     : str | None = None
    mime_type     : str | None = None
    thumbnail_url : str | None = None

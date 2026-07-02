from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title    : str = Field(min_length=1, max_length=100)
    content  : str = Field(default='', max_length=300)
    due_date : datetime | None = None


class TaskUpdate(BaseModel):
    title    : str | None = Field(default=None, min_length=1, max_length=100)
    content  : str | None = Field(default=None, min_length=1, max_length=300)
    due_date : datetime | None = None


class TaskFullUpdate(BaseModel):
    title    : str = Field(min_length=1, max_length=100)
    content  : str = Field(min_length=1, max_length=300)
    due_date : datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id           : int
    title        : str
    content      : str
    creator_id   : int
    owner_id     : int
    workspace_id : int
    due_date     : datetime | None
    is_completed : bool
    completed_at : datetime | None
    date_created : datetime


class PaginatedTaskResponse(BaseModel):
    tasks    : list[TaskResponse]
    total    : int
    skip     : int
    limit    : int
    has_more : bool


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id           : int
    title        : str
    due_date     : datetime | None
    is_completed : bool
    owner_id     : int
    completed_at : datetime | None

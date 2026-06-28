from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title    : str = Field(min_length=1, max_length=100)
    content  : str = Field(default='', max_length=300)
    due_date : datetime | None = None


class TaskUpdate(BaseModel):
    title    : str | None = Field(default=None, min_length=1, max_length=100)
    content  : str | None = Field(default=None, max_length=300)
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
    date_created : datetime


class PaginatedTaskResponse(BaseModel):
    tasks    : list[TaskResponse]
    total    : int
    skip     : int
    limit    : int
    has_more : bool


class TaskMove(BaseModel):
    workspace_id : int


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id           : int
    title        : str
    due_date     : datetime | None
    is_completed : bool
    owner_id     : int

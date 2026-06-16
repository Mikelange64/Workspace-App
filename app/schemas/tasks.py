from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Base(BaseModel):
    pass


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=300)
    creator_id: int
    owner_id: int
    workspace_id: int
    due_date: datetime | None = None


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_completed: bool
    date_created: datetime
    due_date: datetime | None


class PaginatedTaskResponse(Base) :
    tasks    : list[TaskResponse]
    total    : int
    skip     : int
    limit    : int
    has_more : bool


class TaskUpdate(TaskBase):
    title: str | None = None
    content: str | None = Field(default=None, min_length=1, max_length=300)
    creator_id: int | None = None
    owner_id: int | None = None
    workspace_id: int | None = None
    due_date: datetime | None = None


class TaskMove(BaseModel):
    workspace_id: int

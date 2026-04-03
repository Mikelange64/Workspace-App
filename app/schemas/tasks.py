from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime


class Base(BaseModel):
    pass


class TaskBase(BaseModel):
    title     : str = Field(min_length=1, max_length=100)
    content   : str = Field(min_length=1, max_length=300)
    workspace_id : int | None = None
    due_date  : datetime | None = None


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id           : int
    creator_id   : int
    workspace_id : int | None
    date_created : datetime
    due_date     : datetime | None
    is_completed : bool


class TaskUpdate(TaskBase):
    title            : str | None = None
    content      : str | None = Field(default=None, min_length=1, max_length=300)
    workspace_id : int | None = None
    is_completed : bool | None = None
    due_date     : datetime | None = None


class TaskMove(BaseModel):
    workspace_id : int | None
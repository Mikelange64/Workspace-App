from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime
from .users import UserPublic
from .tasks import TaskResponse


class Base(BaseModel):
    pass


class WorkspaceBase(BaseModel):
    admin_id    : int
    title       : str = Field(min_length=1, max_length=50)
    description : str = Field(min_length=1, max_length=500)
    max_number  : int | None = None
    due_date    : datetime | None = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id             : int
    title          : str
    description    : str
    max_number     : int
    num_of_members : int
    num_of_tasks   : int
    date_created   : datetime
    due_date       : datetime | None


class WorkspaceUpdate(WorkspaceBase):
    title        : str | None = Field(min_length=1, max_length=50, default=None)
    description  : str | None = Field(min_length=1, max_length=500, default=None)
    max_number   : int | None = None
    due_date     : datetime | None = None
    is_completed : bool | None = None
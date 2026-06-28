from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name  : str = Field(min_length=1, max_length=50)
    color : str = Field(min_length=1, max_length=50)


class FolderUpdate(BaseModel):
    name  : str | None = Field(min_length=1, max_length=50, default=None)
    color : str | None = Field(min_length=1, max_length=50, default=None)


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id         : int
    owner_id   : int
    name       : str
    color      : str
    created_at : datetime

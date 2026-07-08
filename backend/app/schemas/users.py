from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    username : str   = Field(min_length=5, max_length=50)
    email    : EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    password : str = Field(min_length=8)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id         : int
    username   : str
    image_path : str
    joined_at  : datetime


class UserPrivate(UserPublic):
    email      : EmailStr
    last_login : datetime | None
    

class SuperUserResponse(UserPrivate):
    is_superuser : bool


class PaginatedSuperUserResponse(BaseModel):
    users    : list[SuperUserResponse]
    total    : int
    skip     : int
    limit    : int
    has_more : bool


class UserUpdate(UserBase):
    username   : str | None      = Field(default=None, min_length=5, max_length=50)
    email      : EmailStr | None = Field(default=None,  max_length=120)


class WorkspaceMemberPublic(BaseModel):
    id         : int
    username   : str
    image_path : str
    role       : str
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime

class Base(BaseModel):
    pass

# ======================================================================================================================
# USERS SCHEMAS
# ======================================================================================================================

class UserBase(Base):
    username : str   = Field(min_length=5, max_length=50)
    email : EmailStr = Field(max_length=50)


class UserCreate(UserBase):
    password : str = Field(min_length=8)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id : int
    username : str
    image_path : str
    image_file : str


class UserPrivate(UserPublic):
    email : EmailStr


class UserUpdate(UserCreate):
    username : str | None = Field(min_length=5, max_length=50)
    email : EmailStr | None = Field(max_length=50)
    password : str | None = Field(min_length=8)
    image_path : str | None
    image_file : str | None


class ChangePassword(BaseModel):
    old_password : str
    new_password : str


# ======================================================================================================================
# REMINDERS SCHEMAS
# ======================================================================================================================

class ReminderBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=300)
    due_date : datetime


class ReminderCreate(ReminderBase):
    pass


class ReminderResponse(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id : int
    owner_id : UserPublic
    date_created : datetime
    due_date : datetime
    status : bool


class ReminderUpdate(ReminderBase):
    content : str | None = Field(min_length=1, max_length=300)
    due_date : datetime | None
    status : bool | None
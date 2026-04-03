from pydantic import BaseModel, Field, ConfigDict, EmailStr


class Base(BaseModel):
    pass


class UserBase(Base):
    username : str   = Field(min_length=5, max_length=50)
    email : EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    password : str = Field(min_length=8)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id         : int
    username   : str
    image_path : str | None = None


class UserPrivate(UserPublic):
    email : EmailStr


class UserUpdate(UserBase):
    username   : str | None = Field(default=None, min_length=5, max_length=50)
    email      : EmailStr | None = Field(default=None,  max_length=120)
    image_path : str | None = None


class ChangePassword(BaseModel):
    old_password : str
    new_password : str


class Token(BaseModel):
    access_token: str
    token_type: str
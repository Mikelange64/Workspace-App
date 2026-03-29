from fastapi import FastAPI, APIRouter, HTTPException, Depends, status

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from typing import Annotated

from database import get_db
from models import User
from schemas import UserCreate, UserPublic, UserPrivate, UserUpdate, ChangePassword

router = APIRouter()

@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    email_result = db.execute(select(User).where(func.lower(User.email) == user.email.lower()))
    username_result = db.execute(select(User).where(func.lower(User.username) == user.username))

    email_exists = email_result.scalars().first()
    username_exists = username_result.scalars().first()

    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    if username_exists:
        raise HTTPException(status_code=400, detail="Username already in use")

    new_user = User(
        username=user.username,
        email=user.email.lower(),
        password_hash = user.password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



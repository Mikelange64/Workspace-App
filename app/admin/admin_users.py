from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.models import User
from app.database import get_db
from app.auth import CurrentUser

from typing import Annotated


router = APIRouter()


@router.get("/all")
def get_all_users(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    if not current_user.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not allowed to perform this action")

    result = db.execute(select(User))
    users = result.scalars().all()

    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users")
    return users
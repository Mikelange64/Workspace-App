from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import SuperUserResponse
from app.utility import require_superuser

router = APIRouter()


@router.get("/all", response_model=list[SuperUserResponse])
def get_all_users(
    db        : Annotated[Session, Depends(get_db)],
    superuser : Annotated[User, Depends(require_superuser)],
):
    users = db.execute(select(User)).scalars().all()
    return users


@router.get("/{user_id}", response_model=SuperUserResponse)
def get_user(
    user_id   : int,
    db        : Annotated[Session, Depends(get_db)],
    superuser : Annotated[User, Depends(require_superuser)],
):
    user = db.execute(select(User).where(User.id == user_id)).scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user

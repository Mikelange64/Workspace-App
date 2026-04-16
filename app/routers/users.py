from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, create_access_token, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.models import User, Workspace
from app.schemas.users import (
    ChangePassword,
    Token,
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
)
from app.schemas.workspaces import WorkspaceResponse

router = APIRouter()


@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    email_exists = (
        db.execute(select(User).where(func.lower(User.email) == user.email.lower()))
        .scalars()
        .first()
    )

    username_exists = (
        db.execute(select(User).where(func.lower(User.username) == user.username))
        .scalars()
        .first()
    )

    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    if username_exists:
        raise HTTPException(status_code=400, detail="Username already in use")

    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username, email=user.email.lower(), password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    # here we use the form data username field to accept either email or username, so the user has a choice
    email_or_username = form_data.username.lower()
    user = (
        db.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == email_or_username,
                    func.lower(User.username) == email_or_username,
                )
            )
        )
        .scalars()
        .first()
    )

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incorrect password or email/username",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expired_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
def get_current_user(user: CurrentUser):
    return user


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.get("/me/workspaces", response_model=list[WorkspaceResponse])
def get_user_workspaces(
    current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]
):
    workspace = (
        db.execute(select(Workspace).where(Workspace.admin_id == current_user.id))
        .scalars()
        .all()
    )
    return workspace


@router.patch("/me", response_model=UserPrivate)
def update_user(
    current_user: CurrentUser,
    user_data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    # checks if the user updated their username (not blank or some as before) and if the new username is already taken
    if (
        user_data.username is not None
        and user_data.username.lower() != current_user.username.lower()
    ):
        result = db.execute(select(User).where(User.username == user_data.username))
        existing_username = result.scalars().first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )

    # checks if the user updated their email (not blank or some as before) address and if the new address is already taken
    if (
        user_data.email is not None
        and user_data.email.lower() != current_user.email.lower()
    ):
        result = db.execute(select(User).where(User.email == user_data.email))
        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

    if user_data.username:
        user_data.username = user_data.username.lower()

    if user_data.email:
        user_data.email = user_data.email.lower()

    update = user_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("me/change-password", response_model=UserPrivate)
def change_password(
    current_user: CurrentUser,
    password_data: ChangePassword,
    db: Annotated[Session, Depends(get_db)],
):
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect password"
        )

    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="New password must be different to the old password",
        )

    new_hashed_password = hash_password(password_data.new_password)
    current_user.password_hash = new_hashed_password

    db.commit()
    db.refresh(current_user)

    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    db.delete(current_user)
    db.commit()

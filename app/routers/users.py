from datetime import UTC, datetime, timedelta
from typing import Annotated

from PIL import UnidentifiedImageError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy import delete as sql_delete

from app.auth import (
    CurrentUser, 
    create_access_token, 
    hash_password, 
    verify_password, 
    generate_reset_tokens, 
    hash_reset_token
)
from app.config import settings
from app.database import DbSession
from app.models import User, Workspace, WorkspaceMember, PasswordResetToken
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
    WorkspaceResponse,
)
from app.utils import (
    delete_profile_image,
    get_user_by_id, 
    process_profile_image,
    upload_profile_image, 
    send_password_reset_email
)

from botocore.exceptions import ClientError

router = APIRouter(tags=["users"])


# =======================================================================================
# CRUD ON USERS
# =======================================================================================

@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: DbSession):
    email_exists = (
        db.execute(select(User).where(func.lower(User.email) == user.email.lower()))
        .scalars().first()
    )

    username_exists = (
        db.execute(select(User).where(func.lower(User.username) == user.username))
        .scalars().first()
    )

    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    if username_exists:
        raise HTTPException(status_code=400, detail="Username already registered")

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
    db        : DbSession,
    form_data : Annotated[OAuth2PasswordRequestForm, Depends()],
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
        .scalars().first()
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

    user.last_login = datetime.now(UTC)
    db.commit()

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
def get_current_user(user: CurrentUser):
    return user
    
    
@router.patch("/me", response_model=UserPrivate)
def update_user(current_user: CurrentUser, user_data: UserUpdate, db: DbSession):
    # checks if the user updated their username (not blank or some as before) and if the new username is already taken
    if (
        user_data.username is not None
        and user_data.username.lower() != current_user.username.lower()
    ):
        existing_username = (
            db.execute(select(User).where(User.username == user_data.username))
            .scalars().first()
        )
    
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already registered",
            )

    # checks if the user updated their email (not blank or some as before) address and if the new address is already taken
    if (
        user_data.email is not None
        and user_data.email.lower() != current_user.email.lower()
    ):
        existing_email = (
            db.execute(select(User).where(User.email == user_data.email))
            .scalars()
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

    if user_data.email:
        user_data.email = user_data.email.lower()

    update = user_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(current_user: CurrentUser, db: DbSession):
    old_filename = current_user.image_path

    db.delete(current_user)
    db.commit()

    if old_filename:
       delete_profile_image(old_filename)    


# ========================================================================================
# PASSWORD RESET
# ========================================================================================


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    db               : DbSession,
    request_data     : ForgotPasswordRequest,
    background_tasks : BackgroundTasks,
):
    user = (
        db.execute(select(User)
        .where(func.lower(User.email) == request_data.email.lower()))
        .scalars().first()
    )

    if user:
        # delete existing reset tokens for security
        db.execute(
            sql_delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )

        token      = generate_reset_tokens()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(settings.reset_token_expire_minutes)

        reset_token = PasswordResetToken(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )

        db.add(reset_token)
        db.commit()

        # we send the unhashed token to the user
        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    # for security reasons we don't reveal if the user exists (protect from email enumeration attacks)
    return {
        "message": "If an account exists with this email, you wil recieve password reset instructions"
    }


@router.post("/resert-password")
def reset_password(
    request_data: ResetPasswordRequest, db: DbSession
):
    token_hash = hash_reset_token(request_data.token)

    reset_token = (
        db.execute(select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash))
        .scalars().first()
    )
    
    # if the token doesn't exist
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # if the token is expired
    if reset_token.expires_at < datetime.now(UTC):
        db.delete(reset_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = (
        db.execute(select(User).where(User.id == reset_token.user_id))
        .scalars().first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(request_data.new_password)

    db.execute(
        sql_delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id),
    )
    db.commit()

    return {"message": "Password changed successfully"}


@router.patch("/me/password")
def change_password(
    current_user: CurrentUser,
    password_data: ChangePasswordRequest,
    db: DbSession
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_FORBIDDEN,
            detail="current password is incorrect",
        )

    new_password_hash = hash_password(password_data.new_password)
    current_user.password_hash = new_password_hash

    db.execute(
        sql_delete(PasswordResetToken)
        .where(PasswordResetToken.user_id == current_user.id)
    )

    db.commit()
    return {"message": "Password changed successfully"}

    
# ========================================================================================
# OPERATIOS ON SUBRESOURCES
# ========================================================================================


@router.get("/me/workspaces", response_model=list[WorkspaceResponse])
def get_user_workspaces(current_user: CurrentUser, db: DbSession):
    workspaces = (
        db.execute(select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current_user.id))
        .scalars().all()
    )   
    
    return workspaces


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: DbSession):
    user = get_user_by_id(user_id, db)
    return user


@router.patch("/me/picture", response_model=UserPrivate)
def upload_profile_picture(
    file: UploadFile, current_user: CurrentUser, db: DbSession
):
    content = file.file.read()  # file.file because the app is sync

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        processed_bytes, new_filename = process_profile_image(content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please uplaod a valid image(JPEG, PNG, GIF, WebP).",
        ) from err

    try:
        upload_profile_image(processed_bytes, new_filename)
    except ClientError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to upload image. Please try again",
        ) from err

    old_filename = current_user.image_path  # store the old filename
    current_user.image_path = new_filename

    db.commit()
    db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user


@router.delete("/me/picture", response_model=UserPrivate)
def delete_profile_picture(
    current_user: CurrentUser, db: DbSession,
):
    old_filename = current_user.image_path

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_path = None
    db.commit()
    db.refresh(current_user)

    delete_profile_image(old_filename)
    return current_user
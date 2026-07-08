from datetime import UTC, datetime, timedelta
from typing import Annotated

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select

from app.auth import (
    CurrentUser,
    create_access_token,
    generate_reset_tokens,
    get_current_user,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.config import settings
from app.database import DbSession
from app.dependencies import handle_membership_departure
from app.models import (
    PasswordResetToken,
    RefreshToken,
    User,
    VerificationToken,
    Workspace,
    WorkspaceMember,
)
from app.schemas import (
    ChangePasswordRequest,
    EmailVerification,
    ForgotPasswordRequest,
    RefreshRequest,
    ResendVerificationRequest,
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
    send_password_reset_email,
    send_verification_email,
    upload_profile_image,
)

router = APIRouter(tags=["users"])


# =======================================================================================
# CRUD ON USERS
# =======================================================================================


@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: DbSession):
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
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username, email=user.email.lower(), password_hash=hashed_password
    )

    db.add(new_user)
    db.flush()

    token = generate_reset_tokens()
    token_hash = hash_reset_token(token)
    expires_at = datetime.now(UTC) + timedelta(hours=24)

    db.add(
        VerificationToken(
            user_id=new_user.id, token_hash=token_hash, expires_at=expires_at
        )
    )
    db.commit()
    db.refresh(new_user)

    try:
        send_verification_email(
            to_email=new_user.email, username=new_user.username, token=token
        )
    except Exception:
        pass

    return new_user


@router.post("/login", response_model=Token)
def login(
    db: DbSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
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

    if not user or not  verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password or email/username",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail= "Please verify your email before logging in"
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expired_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    # rotate refresh token: delete old ones, issue a fresh one
    db.execute(sql_delete(RefreshToken).where(RefreshToken.user_id == user.id))
    raw_refresh = generate_reset_tokens()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )

    user.last_login = datetime.now(UTC)
    db.commit()

    return Token(
        access_token=access_token, refresh_token=raw_refresh, token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(body: RefreshRequest, db: DbSession):
    token_hash = hash_reset_token(body.refresh_token)
    stored = (
        db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        .scalars()
        .first()
    )

    if not stored or stored.expires_at < datetime.now(UTC):
        if stored:
            db.delete(stored)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.execute(select(User).where(User.id == stored.user_id)).scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expired_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    # rotate: delete old refresh token, issue a new one
    db.delete(stored)
    raw_refresh = generate_reset_tokens()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()

    return Token(
        access_token=access_token, refresh_token=raw_refresh, token_type="bearer"
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: DbSession):
    token_hash = hash_reset_token(body.refresh_token)
    stored = (
        db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        .scalars()
        .first()
    )
    if stored:
        db.delete(stored)
        db.commit()


@router.get("/me", response_model=UserPrivate)
def get_me(user: CurrentUser):
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
            .scalars()
            .first()
        )

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
    old_filename = current_user.image_file

    memberships = db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == current_user.id)
    ).scalars().all()

    for membership in memberships:
        handle_membership_departure(membership, db)

    db.delete(current_user)
    db.commit()

    if old_filename:
        delete_profile_image(old_filename)


# ========================================================================================
# EMAIL VERIFICATION
# ========================================================================================


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(request_data: EmailVerification, db: DbSession):
    token_hash = hash_reset_token(request_data.token)

    verification_token = (
        db.execute(
            select(VerificationToken).where(VerificationToken.token_hash == token_hash)
        )
        .scalars().first()
    )

    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )

    if verification_token.expires_at < datetime.now(UTC):
        db.delete(verification_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )

    user = (
        db.execute(select(User).where(User.id == verification_token.user_id))
        .scalars()
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )

    user.is_verified = True
    db.delete(verification_token)
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification_email(db: DbSession, request_data: ResendVerificationRequest):
    email_or_username = request_data.identifier.lower()
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

    if user and not user.is_verified:
        db.execute(
            sql_delete(VerificationToken).where(VerificationToken.user_id == user.id)
        )

        token = generate_reset_tokens()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        db.add(
            VerificationToken(
                user_id=user.id, token_hash=token_hash, expires_at=expires_at
            )
        )
        db.commit()

        try:
            send_verification_email(
                to_email=user.email, username=user.username, token=token
            )
        except Exception:
            pass

    return {
        "message": "If an account exists and isn't verified yet, a new verification link has been sent"
    }


# ========================================================================================
# PASSWORD RESET
# ========================================================================================


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(db: DbSession, request_data: ForgotPasswordRequest):
    user = (
        db.execute(
            select(User).where(func.lower(User.email) == request_data.email.lower())
        )
        .scalars()
        .first()
    )

    if user:
        db.execute(
            sql_delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )

        token = generate_reset_tokens()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes
        )

        db.add(
            PasswordResetToken(
                user_id=user.id, token_hash=token_hash, expires_at=expires_at
            )
        )
        db.commit()

        try:
            send_password_reset_email(
                to_email=user.email, username=user.username, token=token
            )
        except Exception:
            pass

    return {
        "message": "If an account exists with this email, you will receive password reset instructions"
    }


@router.post("/reset-password")
def reset_password(request_data: ResetPasswordRequest, db: DbSession):
    token_hash = hash_reset_token(request_data.token)

    reset_token = (
        db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        .scalars()
        .first()
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
        db.execute(select(User).where(User.id == reset_token.user_id)).scalars().first()
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
    current_user: CurrentUser, password_data: ChangePasswordRequest, db: DbSession
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current password is incorrect",
        )

    new_password_hash = hash_password(password_data.new_password)
    current_user.password_hash = new_password_hash

    db.execute(
        sql_delete(PasswordResetToken).where(
            PasswordResetToken.user_id == current_user.id
        )
    )

    db.commit()
    return {"message": "Password changed successfully"}


# ========================================================================================
# OPERATIONS ON SUBRESOURCES
# ========================================================================================


@router.get("/me/workspaces", response_model=list[WorkspaceResponse])
def get_user_workspaces(current_user: CurrentUser, db: DbSession):
    workspaces = (
        db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == current_user.id)
        )
        .scalars()
        .all()
    )

    return workspaces


@router.get( "/search", response_model=UserPublic, dependencies=[Depends(get_current_user)])
def search_user(q: Annotated[str, Query(min_length=1)], db: DbSession):
    user = db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == q.strip().lower(),
                func.lower(User.email) == q.strip().lower(),
            )
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that username or email",
        )

    return user


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: DbSession):
    user = get_user_by_id(user_id, db)
    return user


@router.patch("/me/picture", response_model=UserPrivate)
def upload_profile_picture(file: UploadFile, current_user: CurrentUser, db: DbSession):
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
            detail="Invalid image file. Please upload a valid image(JPEG, PNG, GIF, WebP).",
        ) from err

    try:
        upload_profile_image(processed_bytes, new_filename)
    except ClientError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to upload image. Please try again",
        ) from err

    old_filename = current_user.image_file  # store the old filename
    current_user.image_file = new_filename

    db.commit()
    db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user


@router.delete("/me/picture", response_model=UserPrivate)
def delete_profile_picture(current_user: CurrentUser, db: DbSession,):
    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_file = None
    db.commit()
    db.refresh(current_user)

    delete_profile_image(old_filename)
    return current_user
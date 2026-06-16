from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select

from app.config import settings
from app.database import DbSession
from app.models.users import User

pw_hasher = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")


# =================================== JWT ACCESS TOKEN ===================================


def hash_password(password: str) -> str:
    return pw_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pw_hasher.verify(plain_password, hashed_password)


def create_access_token(data: dict, expired_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expired_delta:
        expire = datetime.now(UTC) + expired_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )

    return encode_jwt


def verify_access_token(token: str) -> bool | str | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except (jwt.PyJWTError, ValueError):
        return False
    else:
        return payload.get("sub")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession,
):
    user_id = verify_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ================================= PASSWORD RESET TOKEN =================================

# url safe base 64 characters
def generate_reset_tokens() -> str:
    return secrets.token_urlsafe(32)


# SHA256 instead of argon2, tokens are longer and harder to brute force
def hash_reset_token(token: str) -> str :
   return hashlib.sha256(token.encode()).hexdigest()
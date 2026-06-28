import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import hash_reset_token
from app.database import DbSession
from app.models import PasswordResetToken, User
from tests.auth_helpers import auth_header, create_test_user, login_user

prefix = "/api/users"

# ========================================================================================
# ASSERTION HELPERS
# ========================================================================================


def assert_auth_error(response):
    assert response.status_code == 401


def count_s3_objects(s3_client, bucket: str) -> int:
    result = s3_client.list_objects_v2(Bucket=bucket)
    return len(result.get("Contents", []))


# ========================================================================================
# FORGOT PASSWORD  (POST /forgot-password)
# ========================================================================================


def test_forgot_password_sends_email(client: TestClient, user):
    """A valid email address triggers the password reset email."""
    target = "app.routers.users.send_password_reset_email"

    with patch(target) as mock_send:
        response = client.post(
            f"{prefix}/forgot-password",
            json={"email": "test@example.com"},
        )

    assert response.status_code == 202
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "test@example.com"
    assert call_kwargs["username"] == "testuser"
    assert "token" in call_kwargs


def test_forgot_password_unknown_email_returns_same_status(client: TestClient):
    """Unknown email returns 202 to avoid email enumeration."""
    target = "app.routers.users.send_password_reset_email"

    with patch(target) as mock_send:
        response = client.post(
            f"{prefix}/forgot-password",
            json={"email": "unknown@example.com"},
        )

    assert response.status_code == 202
    mock_send.assert_not_called()


def test_forgot_password_invalid_email_format(client: TestClient):
    response = client.post(
        f"{prefix}/forgot-password",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


# ========================================================================================
# RESET PASSWORD  (POST /reset-password) — note: endpoint path has a typo "reset-password"
# ========================================================================================


def test_reset_password_success(client: TestClient, db_session):
    """A valid reset token changes the user's password."""
    create_test_user(client)

    # Generate a real reset token for the user
    token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(token)
    user = db_session.execute(select(User)).scalars().first()
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    reset_token = PasswordResetToken(
        user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        f"{prefix}/reset-password",
        json={"token": token, "new_password": "newsecurepassword"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

    # Verify the password actually changed (login with old password fails)
    login_fails = client.post(
        f"{prefix}/login",
        data={"username": "test@example.com", "password": "testpassword123"},
    )
    assert login_fails.status_code == 401

    # Login with new password works
    login_ok = client.post(
        f"{prefix}/login",
        data={"username": "test@example.com", "password": "newsecurepassword"},
    )
    assert login_ok.status_code == 200


def test_reset_password_invalid_token(client: TestClient):
    create_test_user(client)

    response = client.post(
        f"{prefix}/reset-password",
        json={"token": "totally-fake-token", "new_password": "newsecurepassword"},
    )

    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["message"]


def test_reset_password_expired_token(client: TestClient, db_session):
    """An expired token returns 400 and is deleted."""
    create_test_user(client)
    token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(token)
    user = db_session.execute(select(User)).scalars().first()
    expires_at = datetime.now(UTC) - timedelta(hours=1)  # expired
    reset_token = PasswordResetToken(
        user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        f"{prefix}/reset-password",
        json={"token": token, "new_password": "newsecurepassword"},
    )

    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["message"]

    # The expired token should be cleaned up
    remaining = db_session.execute(select(PasswordResetToken)).scalars().all()
    assert len(remaining) == 0


def test_reset_password_missing_new_password(client: TestClient):
    response = client.post(
        f"{prefix}/reset-password",
        json={"token": "some-token"},
    )
    assert response.status_code == 422


def test_reset_password_new_password_too_short(client: TestClient):
    response = client.post(
        f"{prefix}/reset-password",
        json={"token": "some-token", "new_password": "short"},
    )
    assert response.status_code == 422


# ========================================================================================
# UPLOAD PROFILE PICTURE  (PATCH /me/picture)
# ========================================================================================


def test_upload_profile_picture_success(
    client: TestClient, user_auth_headers, mocked_s3, test_image
):
    response = client.patch(
        f"{prefix}/me/picture",
        files={"file": ("profile.jpg", BytesIO(test_image), "image/jpeg")},
        headers=user_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image_path"].startswith("https://")
    assert data["image_path"].endswith(".jpeg")

    # Verify S3 has the uploaded object
    assert count_s3_objects(mocked_s3, "test-bucket") == 1


def test_upload_profile_picture_replaces_old(
    client: TestClient, user_auth_headers, mocked_s3, test_image
):
    """Uploading a second picture removes the old one from S3."""
    # First upload
    client.patch(
        f"{prefix}/me/picture",
        files={"file": ("first.jpg", BytesIO(test_image), "image/jpeg")},
        headers=user_auth_headers,
    )
    assert count_s3_objects(mocked_s3, "test-bucket") == 1

    # Second upload replaces
    response = client.patch(
        f"{prefix}/me/picture",
        files={"file": ("second.jpg", BytesIO(test_image), "image/jpeg")},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    # Still only 1 object in S3 (old one deleted, new one uploaded)
    assert count_s3_objects(mocked_s3, "test-bucket") == 1


def test_upload_profile_picture_no_auth(client: TestClient, test_image):
    response = client.patch(
        f"{prefix}/me/picture",
        files={"file": ("profile.jpg", BytesIO(test_image), "image/jpeg")},
    )
    assert_auth_error(response)


def test_upload_profile_picture_file_too_large(client: TestClient, user_auth_headers):
    """Files exceeding max_upload_size_bytes should be rejected."""
    large_content = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte

    response = client.patch(
        f"{prefix}/me/picture",
        files={"file": ("large.jpg", BytesIO(large_content), "image/jpeg")},
        headers=user_auth_headers,
    )

    assert response.status_code == 400
    assert "File too large" in response.json()["message"]


def test_upload_profile_picture_invalid_file(client: TestClient, user_auth_headers):
    """Non-image files should be rejected."""
    response = client.patch(
        f"{prefix}/me/picture",
        files={"file": ("fake.txt", BytesIO(b"not an image"), "text/plain")},
        headers=user_auth_headers,
    )

    assert response.status_code == 400
    assert "Invalid image file" in response.json()["message"]


# ========================================================================================
# DELETE PROFILE PICTURE  (DELETE /me/picture)
# ========================================================================================


def test_delete_profile_picture_success(
    client: TestClient, user_auth_headers, mocked_s3, test_image
):
    """Upload a picture then delete it."""
    # Upload first
    client.patch(
        f"{prefix}/me/picture",
        files={"file": ("profile.jpg", BytesIO(test_image), "image/jpeg")},
        headers=user_auth_headers,
    )
    assert count_s3_objects(mocked_s3, "test-bucket") == 1

    # Delete it
    response = client.delete(f"{prefix}/me/picture", headers=user_auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["image_path"] == "/static/defaults/default_profile_picture.jpg"

    # S3 object should be gone
    assert count_s3_objects(mocked_s3, "test-bucket") == 0


def test_delete_profile_picture_no_picture(client: TestClient, user_auth_headers):
    """Deleting when no picture exists returns 400."""
    response = client.delete(f"{prefix}/me/picture", headers=user_auth_headers)

    assert response.status_code == 400
    assert "No profile picture" in response.json()["message"]


def test_delete_profile_picture_no_auth(client: TestClient):
    response = client.delete(f"{prefix}/me/picture")
    assert_auth_error(response)


# ========================================================================================
# REGRESSION: DELETE USER also cleans up profile picture from S3
# ========================================================================================


def test_delete_user_removes_s3_picture(
    client: TestClient, user, user_auth_headers, mocked_s3, test_image
):
    """When a user with a profile picture is deleted, the S3 object is also removed."""
    # Upload picture first
    client.patch(
        f"{prefix}/me/picture",
        files={"file": ("profile.jpg", BytesIO(test_image), "image/jpeg")},
        headers=user_auth_headers,
    )
    assert count_s3_objects(mocked_s3, "test-bucket") == 1

    # Delete the user
    response = client.delete(f"{prefix}/me", headers=user_auth_headers)
    assert response.status_code == 204

    # S3 object should be cleaned up
    assert count_s3_objects(mocked_s3, "test-bucket") == 0

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import (
    auth_header,
    create_test_user,
    create_workspace,
    login_user,
    verify_user_in_db,
)

prefix = "/api/users"

# ========================================================================================
# ASSERTION HELPERS
# ========================================================================================


def assert_user_private_shape(response, expected_username=None, expected_email=None):
    """Assert a 200/201 response body has the UserPrivate shape."""
    data = response.json()
    assert "id" in data
    assert "image_path" in data
    assert "joined_at" in data
    assert "last_login" in data
    assert "password" not in data
    assert "password_hash" not in data
    if expected_username is not None:
        assert data["username"] == expected_username
    if expected_email is not None:
        assert data["email"] == expected_email
    return data


def assert_login_success_shape(response):
    """Assert a successful login response has a token."""
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def assert_auth_error(response, expected_message=None):
    """Assert a 401 authentication error, optionally checking the message."""
    assert response.status_code == 401
    if expected_message:
        assert expected_message in response.text


# ========================================================================================
# CREATE USER
# ========================================================================================


def test_create_user_success(client: TestClient):
    response = client.post(
        prefix,
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword",
        },
    )

    assert response.status_code == 201
    assert_user_private_shape(response, "testuser", "test@example.com")


def test_create_user_validation_error(client: TestClient):
    response = client.post(
        prefix,
        json={"username": "testuser"},
    )

    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text


def test_create_user_duplicate_email(client: TestClient):
    create_test_user(client)

    response = client.post(
        prefix,
        json={
            "username": "different_user",
            "email": "test@example.com",
            "password": "testpassword",
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Email already registered"


def test_create_user_duplicate_username(client: TestClient):
    create_test_user(client)

    response = client.post(
        prefix,
        json={
            "username": "testuser",
            "email": "different@example.com",
            "password": "testpassword",
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Username already registered"


# ========================================================================================
# LOGIN
# ========================================================================================


@pytest.mark.parametrize(
    "create_kwargs,login_username",
    [
        pytest.param({}, "test@example.com", id="by_email"),
        pytest.param({}, "testuser", id="by_username"),
        pytest.param(
            {"email": "Test@Example.com"},
            "test@example.com",
            id="case_insensitive_email",
        ),
        pytest.param(
            {"username": "TestUser"}, "testuser", id="case_insensitive_username"
        ),
    ],
)
def test_login_success(client: TestClient, db_session, create_kwargs, login_username):
    create_test_user(client, password="testpassword123", **create_kwargs)
    verify_user_in_db(db_session, create_kwargs.get("email", "test@example.com"))

    response = client.post(
        f"{prefix}/login",
        data={"username": login_username, "password": "testpassword123"},
    )

    assert_login_success_shape(response)


@pytest.mark.parametrize(
    "precreate_kwargs,login_data",
    [
        pytest.param(
            {"password": "correctpassword"},
            {"username": "test@example.com", "password": "wrongpassword"},
            id="wrong_password",
        ),
        pytest.param(
            None,
            {"username": "nonexistent@example.com", "password": "somepassword"},
            id="nonexistent_email",
        ),
        pytest.param(
            None,
            {"username": "unknownuser", "password": "somepassword"},
            id="nonexistent_username",
        ),
    ],
)
def test_login_failure_401(client: TestClient, precreate_kwargs, login_data):
    if precreate_kwargs is not None:
        create_test_user(client, **precreate_kwargs)

    response = client.post(f"{prefix}/login", data=login_data)

    assert response.status_code == 401
    assert response.json()["message"] == "Incorrect password or email/username"


@pytest.mark.parametrize(
    "login_data",
    [
        pytest.param({"username": "test@example.com"}, id="missing_password"),
        pytest.param({"password": "testpassword123"}, id="missing_username"),
    ],
)
def test_login_validation_error(client: TestClient, login_data):
    response = client.post(f"{prefix}/login", data=login_data)

    assert response.status_code == 422


# ========================================================================================
# GET CURRENT USER  (GET /me)
# ========================================================================================


def test_get_me_success(client: TestClient, user_auth_headers):
    response = client.get(f"{prefix}/me", headers=user_auth_headers)

    assert response.status_code == 200
    assert_user_private_shape(response, "testuser", "test@example.com")


def test_get_me_no_token(client: TestClient):
    response = client.get(f"{prefix}/me")

    assert_auth_error(response, "Not authenticated")


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("this.is.a.bad.token", id="invalid_token"),
        pytest.param("not-even-a-jwt", id="malformed_token"),
    ],
)
def test_get_me_bad_token(client: TestClient, token):
    response = client.get(f"{prefix}/me", headers=auth_header(token))

    assert_auth_error(response, "Invalid or expired token")


# ========================================================================================
# GET USER BY ID  (GET /{user_id})
# ========================================================================================


def test_get_user_by_id_success(client: TestClient):
    created = create_test_user(client)

    response = client.get(f"{prefix}/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == created["username"]
    assert data["id"] == created["id"]
    assert "email" not in data
    assert "last_login" not in data


@pytest.mark.parametrize(
    "user_id",
    [
        pytest.param(99999, id="nonexistent"),
        pytest.param(-1, id="negative_id"),
    ],
)
def test_get_user_by_id_not_found(client: TestClient, user_id):
    response = client.get(f"{prefix}/{user_id}")

    assert response.status_code == 404
    assert response.json()["message"] == "User not found"


# ========================================================================================
# GET CURRENT USER'S WORKSPACES  (GET /me/workspaces)
# ========================================================================================


def test_get_user_workspaces_success(client: TestClient, user_token, user_auth_headers):
    create_workspace(client, user_token, title="My First Workspace")

    response = client.get(f"{prefix}/me/workspaces", headers=user_auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "My First Workspace"


def test_get_user_workspaces_multiple(
    client: TestClient, user_token, user_auth_headers
):
    create_workspace(client, user_token, title="Workspace One")
    create_workspace(client, user_token, title="Workspace Two")

    response = client.get(f"{prefix}/me/workspaces", headers=user_auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {w["title"] for w in data}
    assert "Workspace One" in titles
    assert "Workspace Two" in titles


def test_get_user_workspaces_no_workspaces(client: TestClient, user_auth_headers):
    response = client.get(f"{prefix}/me/workspaces", headers=user_auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_get_user_workspaces_no_auth(client: TestClient):
    response = client.get(f"{prefix}/me/workspaces")

    assert_auth_error(response, "Not authenticated")


# ========================================================================================
# UPDATE CURRENT USER  (PATCH /me)
# ========================================================================================


@pytest.mark.parametrize(
    "payload,expected",
    [
        pytest.param(
            {"username": "updateduser"},
            {"username": "updateduser", "email": "test@example.com"},
            id="update_username",
        ),
        pytest.param(
            {"email": "updated@example.com"},
            {"username": "testuser", "email": "updated@example.com"},
            id="update_email",
        ),
        pytest.param(
            {
                "username": "brandnew",
                "email": "brandnew@example.com",
            },
            {
                "username": "brandnew",
                "email": "brandnew@example.com",
            },
            id="update_all_fields",
        ),
    ],
)
def test_update_user_success(client: TestClient, user_auth_headers, payload, expected):
    response = client.patch(f"{prefix}/me", json=payload, headers=user_auth_headers)

    assert response.status_code == 200
    data = response.json()
    for key, value in expected.items():
        assert data[key] == value


def test_update_no_changes_is_noop(client: TestClient, user_auth_headers):
    response = client.patch(
        f"{prefix}/me",
        json={"username": "testuser"},
        headers=user_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_update_empty_body_is_noop(client: TestClient, user_auth_headers):
    response = client.patch(
        f"{prefix}/me",
        json={},
        headers=user_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_update_same_email_is_noop(client: TestClient, user_auth_headers):
    """Updating to the same email (same case) should not raise a conflict."""
    response = client.patch(
        f"{prefix}/me",
        json={"email": "test@example.com"},
        headers=user_auth_headers,
    )

    assert response.status_code == 200


def test_update_email_case_change_is_same_user(client: TestClient, db_session):
    """Changing only the case of the email should be treated as no change (no conflict)."""
    create_test_user(client, email="test@example.com")
    verify_user_in_db(db_session, "test@example.com")
    token = login_user(client)

    response = client.patch(
        f"{prefix}/me",
        json={"email": "TEST@EXAMPLE.COM"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.parametrize(
    "field,conflict_value,expected_message",
    [
        pytest.param(
            "email",
            "user1@example.com",
            "Email already registered",
            id="duplicate_email",
        ),
        pytest.param(
            "username", "user1", "Username already registered", id="duplicate_username"
        ),
    ],
)
def test_update_user_conflict(
    client: TestClient, db_session, field, conflict_value, expected_message
):
    create_test_user(client, username="user1", email="user1@example.com")
    create_test_user(client, username="user2", email="user2@example.com")
    verify_user_in_db(db_session, "user2@example.com")
    token = login_user(client, email="user2@example.com")

    response = client.patch(
        f"{prefix}/me",
        json={field: conflict_value},
        headers=auth_header(token),
    )

    assert response.status_code == 409
    assert expected_message in response.json()["message"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"username": "ab"}, id="username_too_short"),
        pytest.param({"email": "not-an-email"}, id="invalid_email_format"),
    ],
)
def test_update_user_validation_error(client: TestClient, user_auth_headers, payload):
    response = client.patch(f"{prefix}/me", json=payload, headers=user_auth_headers)

    assert response.status_code == 422


def test_update_user_no_auth(client: TestClient):
    response = client.patch(f"{prefix}/me", json={"username": "hacker"})

    assert_auth_error(response, "Not authenticated")


# ========================================================================================
# DELETE CURRENT USER  (DELETE /me)
# ========================================================================================


def test_delete_user_success(client: TestClient, user_auth_headers):
    response = client.delete(f"{prefix}/me", headers=user_auth_headers)

    assert response.status_code == 204


def test_delete_user_removes_user(client: TestClient, user, user_auth_headers):
    client.delete(f"{prefix}/me", headers=user_auth_headers)

    # Verify the user is actually gone
    response = client.get(f"{prefix}/{user['id']}")
    assert response.status_code == 404


def test_delete_user_no_auth(client: TestClient):
    response = client.delete(f"{prefix}/me")

    assert_auth_error(response, "Not authenticated")


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("some.fake.token", id="invalid_token"),
        pytest.param("not-even-a-jwt", id="malformed_token"),
    ],
)
def test_delete_user_bad_token(client: TestClient, token):
    response = client.delete(f"{prefix}/me", headers=auth_header(token))

    assert_auth_error(response, "Invalid or expired token")

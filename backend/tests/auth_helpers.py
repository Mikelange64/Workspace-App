from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def create_test_user(
    client: TestClient,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> dict:
    response = client.post(
        "/api/users", json={"username": username, "email": email, "password": password}
    )
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    return response.json()


def create_superuser(
    client: TestClient,
    username: str = "superuser",
    email: str = "super@example.com",
    password: str = "superpassword123",
) -> dict:
    response = client.post(
        "/api/users", json={"username": username, "email": email, "password": password}
    )
    assert response.status_code == 201, f"Failed to create superuser: {response.text}"
    return response.json()


def create_workspace(
    client: TestClient,
    token: str,
    title: str = "Test Workspace",
    description: str = "A workspace for testing.",
    max_number: int | None = None,
) -> dict:
    body = {
        "title": title,
        "description": description,
    }
    if max_number is not None:
        body["max_number"] = max_number

    response = client.post(
        "/api/workspaces",
        json=body,
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create workspace: {response.text}"
    return response.json()


def add_workspace_member(
    client: TestClient,
    token: str,
    workspace_id: int,
    user_id: int,
) -> dict:
    response = client.patch(
        f"/api/workspaces/{workspace_id}/members/{user_id}",
        headers=auth_header(token),
    )
    assert response.status_code == 200, f"Failed to add member: {response.text}"
    return response.json()


def login_user(
    client: TestClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> str:
    response = client.post(
        "/api/users/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def verify_user_in_db(db_session: Session, email: str) -> None:
    """Mark a test user as email-verified so they can log in (bypasses email flow in tests)."""
    from app.models import User as UserModel
    user = db_session.execute(
        select(UserModel).where(func.lower(UserModel.email) == email.lower())
    ).scalar_one()
    user.is_verified = True
    db_session.flush()


def create_folder(
    client: TestClient,
    token: str,
    name: str = "Test Folder",
    color: str = "#3B82F6",
) -> dict:
    response = client.post(
        "/api/folders",
        json={"name": name, "color": color},
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create folder: {response.text}"
    return response.json()


def create_task(
    client: TestClient,
    token: str,
    workspace_id: int,
    title: str = "Test Task",
    content: str = "Test task content.",
    due_date: str | None = None,
) -> dict:
    body = {
        "title": title,
        "content": content,
        "creator_id": 1,  # ignored by endpoint, overridden from auth
        "owner_id": 1,  # ignored by endpoint, overridden from auth
        "workspace_id": workspace_id,
    }
    if due_date is not None:
        body["due_date"] = due_date

    response = client.post(
        f"/api/workspaces/{workspace_id}/tasks/",
        json=body,
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create task: {response.text}"
    return response.json()

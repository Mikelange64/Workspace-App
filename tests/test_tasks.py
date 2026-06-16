import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from tests.auth_helpers import (
    add_workspace_member,
    auth_header,
    create_task,
    create_test_user,
    create_workspace,
    login_user,
)

taskprefix = "/api/workspaces"


# ========================================================================================
# ASSERTION HELPERS
# ========================================================================================


def assert_task_created(response, expected_title, expected_content):
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == expected_title
    assert data["content"] == expected_content
    assert data["is_completed"] is False
    assert "id" in data
    assert "date_created" in data


def assert_updated_task(response, expected_checks):
    assert response.status_code == 200
    for key, value in expected_checks.items():
        assert response.json()[key] == value
    return response.json()


def assert_forbidden(response):
    assert response.status_code == 403


def assert_unauthorized(response):
    assert response.status_code == 401


# ========================================================================================
# FILE-SCOPED FIXTURES
# ========================================================================================


@pytest.fixture
def task(client, user_token, workspace):
    """Create and return a task owned by the default user in their workspace."""
    return create_task(client, user_token, workspace["id"])


# ========================================================================================
# CREATE TASK
# ========================================================================================


def test_create_task_as_admin_success(client: TestClient, user_auth_headers, workspace):
    response = client.post(
        f"{taskprefix}/{workspace['id']}/tasks/",
        json={
            "title": "My Task",
            "content": "Task content here.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": workspace["id"],
        },
        headers=user_auth_headers,
    )
    assert_task_created(response, "My Task", "Task content here.")
    assert response.json()["workspace_id"] == workspace["id"]
    assert response.json()["creator_id"] is not None


def test_create_task_as_regular_member_success(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")
    response = client.post(
        f"{taskprefix}/{workspace['id']}/tasks/",
        json={
            "title": "Member Task",
            "content": "Created by a regular member.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": workspace["id"],
        },
        headers=auth_header(member_token),
    )
    assert response.status_code == 201
    assert response.json()["creator_id"] == second_user["id"]
    assert response.json()["owner_id"] == second_user["id"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"content": "No title here.", "creator_id": 1, "owner_id": 1},
            id="missing_title",
        ),
        pytest.param(
            {"title": "No Content", "creator_id": 1, "owner_id": 1},
            id="missing_content",
        ),
    ],
)
def test_create_task_validation_error(
    client: TestClient, user_token, workspace, payload
):
    payload["workspace_id"] = workspace["id"]
    response = client.post(
        f"{taskprefix}/{workspace['id']}/tasks/",
        json=payload,
        headers=auth_header(user_token),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_create_task_auth_failures(
    client: TestClient, user_token, workspace, token, expected_status
):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.post(
        f"{taskprefix}/{workspace['id']}/tasks/",
        json={
            "title": "Hacker",
            "content": "Hack.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": workspace["id"],
        },
        **kwargs,
    )
    assert response.status_code == expected_status


def test_create_task_nonexistent_workspace(client: TestClient, user_auth_headers):
    response = client.post(
        f"{taskprefix}/99999/tasks/",
        json={
            "title": "Ghost",
            "content": "Ghost.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": 99999,
        },
        headers=user_auth_headers,
    )
    assert_forbidden(response)


# ========================================================================================
# GET TASKS (LIST)
# ========================================================================================


def test_get_tasks_empty(client: TestClient, user_auth_headers, workspace):
    response = client.get(
        f"{taskprefix}/{workspace['id']}/tasks/", headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tasks"] == []
    assert data["total"] == 0
    assert data["has_more"] is False


def test_get_tasks_multiple(
    client: TestClient, user_token, user_auth_headers, workspace
):
    create_task(client, user_token, workspace["id"], title="Task One")
    create_task(client, user_token, workspace["id"], title="Task Two")
    response = client.get(
        f"{taskprefix}/{workspace['id']}/tasks/", headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert {t["title"] for t in data["tasks"]} == {"Task One", "Task Two"}


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_get_tasks_auth_failures(client: TestClient, workspace, token, expected_status):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.get(f"{taskprefix}/{workspace['id']}/tasks/", **kwargs)
    assert response.status_code == expected_status


def test_get_tasks_nonexistent_workspace(client: TestClient, user_auth_headers):
    response = client.get(f"{taskprefix}/99999/tasks/", headers=user_auth_headers)
    assert_forbidden(response)


# ========================================================================================
# GET SINGLE TASK
# ========================================================================================


def test_get_task_success(client: TestClient, user_auth_headers, task):
    response = client.get(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


def test_get_task_nonexistent(client: TestClient, user_auth_headers, workspace):
    response = client.get(
        f"{taskprefix}/{workspace['id']}/tasks/99999", headers=user_auth_headers
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_get_task_auth_failures(client: TestClient, task, token, expected_status):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.get(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}", **kwargs
    )
    assert response.status_code == expected_status


# ========================================================================================
# UPDATE TASK PARTIAL  (PATCH)
# ========================================================================================


@pytest.mark.parametrize(
    "payload,expected",
    [
        pytest.param(
            {"title": "Updated Title"}, {"title": "Updated Title"}, id="update_title"
        ),
        pytest.param(
            {"content": "Updated content."},
            {"content": "Updated content."},
            id="update_content",
        ),
        pytest.param(
            {"title": "Completely New", "content": "Completely new content."},
            {"title": "Completely New", "content": "Completely new content."},
            id="update_all_fields",
        ),
    ],
)
def test_update_task_success(
    client: TestClient, user_auth_headers, task, payload, expected
):
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/",
        json=payload,
        headers=user_auth_headers,
    )
    assert_updated_task(response, expected)


def test_update_task_empty_body_noop(client: TestClient, user_auth_headers, task):
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/",
        json={},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == task["title"]


def test_update_task_nonexistent(client: TestClient, user_auth_headers, workspace):
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/99999/",
        json={"title": "Ghost"},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_update_task_auth_failures(client: TestClient, task, token, expected_status):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/",
        json={"title": "Hacked!"},
        **kwargs,
    )
    assert response.status_code == expected_status


def test_update_task_validation_error(client: TestClient, user_auth_headers, task):
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/",
        json={"content": ""},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


# ========================================================================================
# UPDATE TASK FULL  (PUT)
# ========================================================================================


def test_full_update_task_as_owner_success(
    client: TestClient, user, user_auth_headers, task
):
    response = client.put(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        json={
            "title": "Full Update",
            "content": "Fully updated.",
            "creator_id": user["id"],
            "owner_id": user["id"],
            "workspace_id": task["workspace_id"],
        },
        headers=user_auth_headers,
    )
    assert_updated_task(response, {"title": "Full Update", "content": "Fully updated."})


def test_full_update_task_as_owner_all_fields(
    client: TestClient, user, user_auth_headers, task
):
    response = client.put(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        json={
            "title": "Complete",
            "content": "Complete.",
            "creator_id": user["id"],
            "owner_id": user["id"],
            "workspace_id": task["workspace_id"],
            "due_date": None,
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 200


def test_full_update_task_non_owner_member(
    client: TestClient, user_token, user_auth_headers, task
):
    other_user = create_test_user(client, username="other", email="other@example.com")
    add_workspace_member(client, user_token, task["workspace_id"], other_user["id"])
    other_token = login_user(client, email="other@example.com")
    response = client.put(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        json={
            "title": "Nope",
            "content": "Nope.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": task["workspace_id"],
        },
        headers=auth_header(other_token),
    )
    assert response.status_code == 401
    assert "not authorized" in response.json()["message"].lower()


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_full_update_task_auth_failures(
    client: TestClient, task, token, expected_status
):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.put(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        json={
            "title": "Hack",
            "content": "Hack.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": task["workspace_id"],
        },
        **kwargs,
    )
    assert response.status_code == expected_status


def test_full_update_task_missing_fields(client: TestClient, user_auth_headers, task):
    response = client.put(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        json={"title": "Missing Content"},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


def test_full_update_task_nonexistent(client: TestClient, user_auth_headers, workspace):
    response = client.put(
        f"{taskprefix}/{workspace['id']}/tasks/99999",
        json={
            "title": "Ghost",
            "content": "Ghost.",
            "creator_id": 1,
            "owner_id": 1,
            "workspace_id": workspace["id"],
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# DELETE TASK
# ========================================================================================


def test_delete_task_as_admin_success(client: TestClient, user_auth_headers, task):
    response = client.delete(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 204


def test_delete_task_removes_task(client: TestClient, user_auth_headers, task):
    client.delete(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        headers=user_auth_headers,
    )
    response = client.get(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 404


def test_delete_task_as_non_admin_member(
    client: TestClient, user_token, user_auth_headers, task, second_user
):
    add_workspace_member(client, user_token, task["workspace_id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")
    response = client.delete(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}",
        headers=auth_header(member_token),
    )
    assert_forbidden(response)


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_delete_task_auth_failures(client: TestClient, task, token, expected_status):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.delete(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}", **kwargs
    )
    assert response.status_code == expected_status


def test_delete_task_nonexistent(client: TestClient, user_auth_headers, workspace):
    response = client.delete(
        f"{taskprefix}/{workspace['id']}/tasks/99999", headers=user_auth_headers
    )
    assert response.status_code == 404


# ========================================================================================
# COMPLETE TASK
# NOTE: Known bug — condition `task.owner_id == current_user.user_id` is inverted.
# Current behavior blocks the owner and allows non-owners. Tests match current behavior.
# ========================================================================================


def test_complete_task_as_non_owner_success(
    client: TestClient, user_token, user_auth_headers, task
):
    other_user = create_test_user(client, username="other", email="other@example.com")
    add_workspace_member(client, user_token, task["workspace_id"], other_user["id"])
    other_token = login_user(client, email="other@example.com")
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/complete",
        headers=auth_header(other_token),
    )
    assert response.status_code == 200
    assert response.json()["is_completed"] is True


def test_complete_task_owner_blocked(client: TestClient, user_auth_headers, task):
    """BUG: Owner cannot complete their own task due to inverted condition."""
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/complete",
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_complete_task_nonexistent(client: TestClient, user_auth_headers, workspace):
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/99999/complete",
        headers=user_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_complete_task_auth_failures(client: TestClient, task, token, expected_status):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/complete", **kwargs
    )
    assert response.status_code == expected_status


# ========================================================================================
# CHANGE TASK OWNER
# ========================================================================================


def test_make_owner_success(
    client: TestClient, user_token, user_auth_headers, task, second_user
):
    add_workspace_member(client, user_token, task["workspace_id"], second_user["id"])
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/owner",
        params={"user_id": second_user["id"]},
        headers=user_auth_headers,
    )
    assert response.status_code == 200


def test_make_owner_self(client: TestClient, user, user_auth_headers, task):
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/owner",
        params={"user_id": user["id"]},
        headers=user_auth_headers,
    )
    assert response.status_code == 200


def test_make_owner_target_not_member(client: TestClient, user_auth_headers, task):
    stranger = create_test_user(
        client, username="stranger", email="stranger@example.com"
    )
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/owner",
        params={"user_id": stranger["id"]},
        headers=user_auth_headers,
    )
    assert_forbidden(response)


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("regular", 403, id="non_admin"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_make_owner_auth_failures(
    client: TestClient,
    user_token,
    user_auth_headers,
    task,
    second_user,
    token,
    expected_status,
):
    add_workspace_member(client, user_token, task["workspace_id"], second_user["id"])
    headers = None
    if token == "regular":
        regular_user = create_test_user(
            client, username="regular", email="regular@example.com"
        )
        add_workspace_member(
            client, user_token, task["workspace_id"], regular_user["id"]
        )
        regular_token = login_user(client, email="regular@example.com")
        headers = auth_header(regular_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/owner",
        params={"user_id": second_user["id"]},
        **kwargs,
    )
    assert response.status_code == expected_status


def test_make_owner_nonexistent_task(
    client: TestClient, user_token, second_user, user_auth_headers, workspace
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/99999/owner",
        params={"user_id": second_user["id"]},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# MOVE TASK
# ========================================================================================


def test_move_task_success(
    client: TestClient, user_token, user_auth_headers, workspace, task
):
    workspace_b = create_workspace(client, user_token, title="Workspace B")
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/{task['id']}/move",
        json={"workspace_id": workspace_b["id"]},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == workspace_b["id"]


def test_move_task_verified(
    client: TestClient, user_token, user_auth_headers, workspace, task
):
    workspace_b = create_workspace(client, user_token, title="Workspace B")
    client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/{task['id']}/move",
        json={"workspace_id": workspace_b["id"]},
        headers=user_auth_headers,
    )
    # Task should be in workspace_b's task list
    response = client.get(
        f"{taskprefix}/{workspace_b['id']}/tasks/", headers=user_auth_headers
    )
    assert any(t["id"] == task["id"] for t in response.json()["tasks"])
    # Task should no longer be in workspace_a's task list
    response = client.get(
        f"{taskprefix}/{workspace['id']}/tasks/", headers=user_auth_headers
    )
    assert not any(t["id"] == task["id"] for t in response.json()["tasks"])


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("regular", 403, id="non_admin"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_move_task_auth_failures(
    client: TestClient,
    user_token,
    user_auth_headers,
    workspace,
    task,
    token,
    expected_status,
):
    workspace_b = create_workspace(client, user_token, title="Workspace B")
    headers = None
    if token == "regular":
        regular_user = create_test_user(
            client, username="regular", email="regular@example.com"
        )
        add_workspace_member(client, user_token, workspace["id"], regular_user["id"])
        regular_token = login_user(client, email="regular@example.com")
        headers = auth_header(regular_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/{task['id']}/move",
        json={"workspace_id": workspace_b["id"]},
        **kwargs,
    )
    assert response.status_code == expected_status


def test_move_task_nonexistent_target_workspace(
    client: TestClient, user_auth_headers, task
):
    with pytest.raises(IntegrityError):
        client.patch(
            f"{taskprefix}/{task['workspace_id']}/tasks/{task['id']}/move",
            json={"workspace_id": 99999},
            headers=user_auth_headers,
        )


def test_move_task_nonexistent_task(
    client: TestClient, user_token, user_auth_headers, workspace
):
    workspace_b = create_workspace(client, user_token, title="Workspace B")
    response = client.patch(
        f"{taskprefix}/{workspace['id']}/tasks/99999/move",
        json={"workspace_id": workspace_b["id"]},
        headers=user_auth_headers,
    )
    assert response.status_code == 404

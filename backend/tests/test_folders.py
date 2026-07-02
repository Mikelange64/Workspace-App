import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_header, create_folder, create_test_user, login_user

folderprefix = "/api/folders"


# ========================================================================================
# FIXTURES
# ========================================================================================


@pytest.fixture
def folder(client, user_token):
    """Create and return a folder owned by the default user."""
    return create_folder(client, user_token)


# ========================================================================================
# ASSERTION HELPERS
# ========================================================================================


def assert_folder(response, expected_name, expected_color):
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == expected_name
    assert data["color"] == expected_color
    assert "id" in data
    assert "owner_id" in data
    assert "created_at" in data


# ========================================================================================
# CREATE  (POST /api/folders)
# ========================================================================================


def test_create_folder_success(client: TestClient, user_auth_headers):
    response = client.post(
        folderprefix, json={"name": "Design", "color": "#6366F1"}, headers=user_auth_headers
    )
    assert_folder(response, "Design", "#6366F1")


def test_create_folder_records_owner(client: TestClient, user, user_auth_headers):
    response = client.post(
        folderprefix, json={"name": "My Folder", "color": "#red"}, headers=user_auth_headers
    )
    assert response.status_code == 201
    assert response.json()["owner_id"] == user["id"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"color": "#FF0000"}, id="missing_name"),
        pytest.param({"name": "Folder"}, id="missing_color"),
        pytest.param({"name": "", "color": "#FF0000"}, id="empty_name"),
        pytest.param({"name": "Folder", "color": ""}, id="empty_color"),
    ],
)
def test_create_folder_validation_error(client: TestClient, user_auth_headers, payload):
    response = client.post(folderprefix, json=payload, headers=user_auth_headers)
    assert response.status_code == 422


def test_create_folder_no_auth(client: TestClient):
    response = client.post(folderprefix, json={"name": "Folder", "color": "#red"})
    assert response.status_code == 401


# ========================================================================================
# LIST  (GET /api/folders)
# ========================================================================================


def test_list_folders_empty(client: TestClient, user_auth_headers):
    response = client.get(folderprefix, headers=user_auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_folders_returns_own(client: TestClient, user_token, user_auth_headers):
    create_folder(client, user_token, name="A")
    create_folder(client, user_token, name="B")
    response = client.get(folderprefix, headers=user_auth_headers)
    assert response.status_code == 200
    names = {f["name"] for f in response.json()}
    assert names == {"A", "B"}


def test_list_folders_isolation(client: TestClient, user_token, user_auth_headers, second_user_token):
    """Each user only sees their own folders."""
    create_folder(client, user_token, name="Owner Folder")
    create_folder(client, second_user_token, name="Other Folder")
    response = client.get(folderprefix, headers=user_auth_headers)
    names = {f["name"] for f in response.json()}
    assert "Owner Folder" in names
    assert "Other Folder" not in names


def test_list_folders_no_auth(client: TestClient):
    response = client.get(folderprefix)
    assert response.status_code == 401


# ========================================================================================
# UPDATE  (PATCH /api/folders/{id})
# ========================================================================================


@pytest.mark.parametrize(
    "payload,expected",
    [
        pytest.param({"name": "Renamed"}, {"name": "Renamed"}, id="update_name"),
        pytest.param({"color": "#00FF00"}, {"color": "#00FF00"}, id="update_color"),
        pytest.param({"name": "New", "color": "#000"}, {"name": "New", "color": "#000"}, id="update_both"),
    ],
)
def test_update_folder_success(client: TestClient, user_auth_headers, folder, payload, expected):
    response = client.patch(
        f"{folderprefix}/{folder['id']}", json=payload, headers=user_auth_headers
    )
    assert response.status_code == 200
    for key, value in expected.items():
        assert response.json()[key] == value


def test_update_folder_empty_body_noop(client: TestClient, user_auth_headers, folder):
    response = client.patch(
        f"{folderprefix}/{folder['id']}", json={}, headers=user_auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == folder["name"]
    assert response.json()["color"] == folder["color"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"name": ""}, id="empty_name"),
        pytest.param({"color": ""}, id="empty_color"),
    ],
)
def test_update_folder_validation_error(client: TestClient, user_auth_headers, folder, payload):
    response = client.patch(
        f"{folderprefix}/{folder['id']}", json=payload, headers=user_auth_headers
    )
    assert response.status_code == 422


def test_update_folder_not_found(client: TestClient, user_auth_headers):
    response = client.patch(
        f"{folderprefix}/99999", json={"name": "Ghost"}, headers=user_auth_headers
    )
    assert response.status_code == 404


def test_update_folder_other_users_folder(
    client: TestClient, user_auth_headers, second_user_token
):
    other_folder = create_folder(client, second_user_token, name="Theirs")
    response = client.patch(
        f"{folderprefix}/{other_folder['id']}",
        json={"name": "Stolen"},
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_update_folder_no_auth(client: TestClient, folder):
    response = client.patch(f"{folderprefix}/{folder['id']}", json={"name": "No auth"})
    assert response.status_code == 401


# ========================================================================================
# DELETE  (DELETE /api/folders/{id})
# ========================================================================================


def test_delete_folder_success(client: TestClient, user_auth_headers, folder):
    response = client.delete(f"{folderprefix}/{folder['id']}", headers=user_auth_headers)
    assert response.status_code == 204


def test_delete_folder_removes_folder(client: TestClient, user_token, user_auth_headers, folder):
    client.delete(f"{folderprefix}/{folder['id']}", headers=user_auth_headers)
    response = client.get(folderprefix, headers=user_auth_headers)
    assert not any(f["id"] == folder["id"] for f in response.json())


def test_delete_folder_nullifies_workspace_folder_id(
    client: TestClient, user_token, user_auth_headers, workspace, folder
):
    """Deleting a folder should unlink any workspaces assigned to it."""
    client.patch(
        f"/api/workspaces/{workspace['id']}",
        json={"folder_id": folder["id"]},
        headers=user_auth_headers,
    )
    client.delete(f"{folderprefix}/{folder['id']}", headers=user_auth_headers)
    response = client.get(f"/api/workspaces/{workspace['id']}", headers=user_auth_headers)
    assert response.json()["folder_id"] is None


def test_delete_folder_not_found(client: TestClient, user_auth_headers):
    response = client.delete(f"{folderprefix}/99999", headers=user_auth_headers)
    assert response.status_code == 404


def test_delete_folder_other_users_folder(
    client: TestClient, user_auth_headers, second_user_token
):
    other_folder = create_folder(client, second_user_token, name="Theirs")
    response = client.delete(
        f"{folderprefix}/{other_folder['id']}", headers=user_auth_headers
    )
    assert response.status_code == 403


def test_delete_folder_no_auth(client: TestClient, folder):
    response = client.delete(f"{folderprefix}/{folder['id']}")
    assert response.status_code == 401

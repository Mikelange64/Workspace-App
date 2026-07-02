import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import (
    add_workspace_member,
    auth_header,
    create_test_user,
    create_workspace,
    login_user,
    verify_user_in_db,
)

wsprefix = "/api/workspaces"


# ========================================================================================
# ASSERTION HELPERS
# ========================================================================================


def assert_workspace_created(response, expected_title, expected_description):
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == expected_title
    assert data["description"] == expected_description
    assert "id" in data
    assert "date_created" in data
    assert data["num_of_members"] == 1
    assert data["num_of_tasks"] == 0


def assert_updated_workspace(response, expected_checks):
    assert response.status_code == 200
    for key, value in expected_checks.items():
        assert response.json()[key] == value
    return response.json()


def assert_forbidden(response):
    assert response.status_code == 403


def assert_unauthorized(response):
    assert response.status_code == 401


# ========================================================================================
# CREATE WORKSPACE
# ========================================================================================


def test_create_workspace_success(client: TestClient, user_auth_headers):
    response = client.post(
        wsprefix,
        json={"title": "My Project", "description": "A cool project workspace."},
        headers=user_auth_headers,
    )
    assert_workspace_created(response, "My Project", "A cool project workspace.")


def test_create_workspace_with_optional_fields(client: TestClient, user_auth_headers):
    response = client.post(
        wsprefix,
        json={
            "title": "Full Workspace",
            "description": "With optional fields.",
            "max_number": 10,
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["max_number"] == 10


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"description": "No title here."}, id="missing_title"),
        pytest.param({"title": "", "description": "Empty title"}, id="empty_title"),
        pytest.param({"title": "No Description"}, id="missing_description"),
    ],
)
def test_create_workspace_validation_error(
    client: TestClient, user_auth_headers, payload
):
    response = client.post(wsprefix, json=payload, headers=user_auth_headers)
    assert response.status_code == 422


def test_create_workspace_no_auth(client: TestClient):
    response = client.post(
        wsprefix, json={"title": "Hacker", "description": "No token."}
    )
    assert_unauthorized(response)


# ========================================================================================
# GET WORKSPACE
# ========================================================================================


def test_get_workspace_success(client: TestClient, workspace, user_auth_headers):
    response = client.get(f"{wsprefix}/{workspace['id']}", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workspace["id"]
    assert data["title"] == workspace["title"]
    assert data["num_of_members"] == 1


@pytest.mark.parametrize(
    "workspace_id",
    [
        pytest.param(99999, id="nonexistent"),
        pytest.param(-1, id="negative_id"),
    ],
)
def test_get_workspace_not_found(client: TestClient, user_auth_headers, workspace_id):
    response = client.get(f"{wsprefix}/{workspace_id}", headers=user_auth_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Workspace not found"


# ========================================================================================
# UPDATE WORKSPACE PARTIAL  (PATCH)
# ========================================================================================


@pytest.mark.parametrize(
    "payload,expected",
    [
        pytest.param(
            {"title": "Updated Title"}, {"title": "Updated Title"}, id="update_title"
        ),
        pytest.param(
            {"description": "Updated description."},
            {"description": "Updated description."},
            id="update_description",
        ),
        pytest.param({"max_number": 25}, {"max_number": 25}, id="update_max_number"),
        pytest.param(
            {
                "title": "Completely New",
                "description": "Brand new description.",
                "max_number": 50,
            },
            {
                "title": "Completely New",
                "description": "Brand new description.",
                "max_number": 50,
            },
            id="update_all_fields",
        ),
    ],
)
def test_update_workspace_success(
    client: TestClient, user_auth_headers, workspace, payload, expected
):
    response = client.patch(
        f"{wsprefix}/{workspace['id']}", json=payload, headers=user_auth_headers
    )
    assert_updated_workspace(response, expected)


def test_update_workspace_empty_body_noop(
    client: TestClient, user_auth_headers, workspace
):
    response = client.patch(
        f"{wsprefix}/{workspace['id']}", json={}, headers=user_auth_headers
    )
    assert_updated_workspace(
        response, {"title": workspace["title"], "description": workspace["description"]}
    )


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("intruder", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_update_workspace_auth_failures(
    client: TestClient, db_session, workspace, token, expected_status
):
    headers = None
    if token == "intruder":
        create_test_user(client, username="intruder", email="intruder@example.com")
        verify_user_in_db(db_session, "intruder@example.com")
        intruder_token = login_user(client, email="intruder@example.com")
        headers = auth_header(intruder_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{wsprefix}/{workspace['id']}", json={"title": "Hacked!"}, **kwargs
    )
    assert response.status_code == expected_status


def test_update_workspace_nonexistent(client: TestClient, user_auth_headers):
    response = client.patch(
        f"{wsprefix}/99999", json={"title": "Ghost"}, headers=user_auth_headers
    )
    assert_forbidden(response)


def test_update_workspace_validation_error(
    client: TestClient, user_auth_headers, workspace
):
    response = client.patch(
        f"{wsprefix}/{workspace['id']}", json={"title": ""}, headers=user_auth_headers
    )
    assert response.status_code == 422


# ========================================================================================
# UPDATE WORKSPACE FULL  (PUT)
# ========================================================================================


def test_full_update_workspace_success(
    client: TestClient, user_auth_headers, workspace
):
    response = client.put(
        f"{wsprefix}/{workspace['id']}/",
        json={
            "title": "Full Replacement",
            "description": "Complete new description.",
            "max_number": 15,
            "due_date": None,
        },
        headers=user_auth_headers,
    )
    assert_updated_workspace(
        response,
        {
            "title": "Full Replacement",
            "description": "Complete new description.",
            "max_number": 15,
        },
    )


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("intruder", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_full_update_workspace_auth_failures(
    client: TestClient, db_session, workspace, token, expected_status
):
    headers = None
    if token == "intruder":
        create_test_user(client, username="intruder", email="intruder@example.com")
        verify_user_in_db(db_session, "intruder@example.com")
        intruder_token = login_user(client, email="intruder@example.com")
        headers = auth_header(intruder_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.put(
        f"{wsprefix}/{workspace['id']}/",
        json={"title": "Hacked", "description": "Hacked."},
        **kwargs,
    )
    assert response.status_code == expected_status


def test_full_update_workspace_missing_fields(
    client: TestClient, user_auth_headers, workspace
):
    response = client.put(
        f"{wsprefix}/{workspace['id']}/",
        json={"title": "Missing Description"},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


def test_full_update_workspace_nonexistent(client: TestClient, user_auth_headers):
    response = client.put(
        f"{wsprefix}/99999/",
        json={"title": "Ghost", "description": "Ghost."},
        headers=user_auth_headers,
    )
    assert_forbidden(response)


# ========================================================================================
# DELETE WORKSPACE
# ========================================================================================


def test_delete_workspace_as_admin_success(
    client: TestClient, user_auth_headers, workspace
):
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/", headers=user_auth_headers
    )
    assert response.status_code == 204


def test_delete_workspace_removes_workspace(
    client: TestClient, user_auth_headers, workspace
):
    client.delete(f"{wsprefix}/{workspace['id']}/", headers=user_auth_headers)
    response = client.get(f"{wsprefix}/{workspace['id']}", headers=user_auth_headers)
    assert response.status_code == 404


def test_delete_workspace_as_non_admin_member(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/", headers=auth_header(member_token)
    )
    assert_forbidden(response)


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("stranger", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_delete_workspace_auth_failures(
    client: TestClient, db_session, workspace, token, expected_status
):
    headers = None
    if token == "stranger":
        create_test_user(client, username="stranger", email="stranger@example.com")
        verify_user_in_db(db_session, "stranger@example.com")
        token = login_user(client, email="stranger@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.delete(f"{wsprefix}/{workspace['id']}/", **kwargs)
    assert response.status_code == expected_status


def test_delete_workspace_nonexistent(client: TestClient, user_auth_headers):
    response = client.delete(f"{wsprefix}/99999/", headers=user_auth_headers)
    assert_forbidden(response)


# ========================================================================================
# GET MEMBERS
# ========================================================================================


def test_get_members_success(client: TestClient, user_auth_headers, workspace):
    response = client.get(
        f"{wsprefix}/{workspace['id']}/members", headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["username"] == "testuser"


def test_get_members_after_adding_user(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.get(
        f"{wsprefix}/{workspace['id']}/members", headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    usernames = {m["username"] for m in data}
    assert "testuser" in usernames
    assert "user2" in usernames


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_get_members_auth_failures(
    client: TestClient, db_session, workspace, token, expected_status
):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        verify_user_in_db(db_session, "outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.get(f"{wsprefix}/{workspace['id']}/members", **kwargs)
    assert response.status_code == expected_status


def test_get_members_nonexistent_workspace(client: TestClient, user_auth_headers):
    response = client.get(f"{wsprefix}/99999/members", headers=user_auth_headers)
    assert_forbidden(response)


# ========================================================================================
# ADD MEMBER
# ========================================================================================


def test_add_member_success(
    client: TestClient, user_auth_headers, workspace, second_user
):
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["num_of_members"] == 2


def test_add_member_already_exists(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["message"] == "User already in the workspace"


def test_add_member_nonexistent_user(client: TestClient, user_auth_headers, workspace):
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/999999", headers=user_auth_headers
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("regular", 403, id="non_admin"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_add_member_auth_failures(
    client: TestClient,
    db_session,
    user_token,
    user_auth_headers,
    workspace,
    second_user,
    token,
    expected_status,
):
    headers = None
    if token == "regular":
        regular_user = create_test_user(
            client, username="regular", email="regular@example.com"
        )
        add_workspace_member(client, user_token, workspace["id"], regular_user["id"])
        verify_user_in_db(db_session, "regular@example.com")
        regular_token = login_user(client, email="regular@example.com")
        headers = auth_header(regular_token)
    target = create_test_user(client, username="target", email="target@example.com")
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{target['id']}", **kwargs
    )
    assert response.status_code == expected_status


def test_add_member_nonexistent_workspace(
    client: TestClient, user_auth_headers, second_user
):
    response = client.patch(
        f"{wsprefix}/99999/members/{second_user['id']}", headers=user_auth_headers
    )
    assert_forbidden(response)


# ========================================================================================
# MAKE ADMIN
# ========================================================================================


def test_make_admin_success(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}/admin",
        headers=user_auth_headers,
    )
    assert response.status_code == 200


def test_make_admin_already_admin_is_noop(
    client: TestClient, user, user_auth_headers, workspace
):
    """Promoting the creator (already admin) is a noop."""
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{user['id']}/admin",
        headers=user_auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("regular_member", 403, id="non_admin"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_make_admin_auth_failures(
    client: TestClient,
    db_session,
    user_token,
    user_auth_headers,
    workspace,
    second_user,
    token,
    expected_status,
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    headers = None
    if token == "regular_member":
        regular_user = create_test_user(
            client, username="regular", email="regular@example.com"
        )
        add_workspace_member(client, user_token, workspace["id"], regular_user["id"])
        verify_user_in_db(db_session, "regular@example.com")
        regular_token = login_user(client, email="regular@example.com")
        headers = auth_header(regular_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}/admin", **kwargs
    )
    assert response.status_code == expected_status


def test_make_admin_target_not_member(client: TestClient, user_auth_headers, workspace):
    stranger = create_test_user(
        client, username="stranger", email="stranger@example.com"
    )
    response = client.patch(
        f"{wsprefix}/{workspace['id']}/members/{stranger['id']}/admin",
        headers=user_auth_headers,
    )
    assert_forbidden(response)


# ========================================================================================
# LEAVE WORKSPACE
# ========================================================================================


def test_leave_workspace_as_member_success(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/me", headers=auth_header(member_token)
    )
    assert response.status_code == 204


def test_leave_workspace_as_member_removes_from_workspace(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")
    client.delete(
        f"{wsprefix}/{workspace['id']}/members/me", headers=auth_header(member_token)
    )
    response = client.get(
        f"{wsprefix}/{workspace['id']}/members", headers=user_auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_leave_workspace_as_admin_with_other_admin(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    client.patch(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}/admin",
        headers=user_auth_headers,
    )
    second_token = login_user(client, email="user2@example.com")
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/me", headers=auth_header(second_token)
    )
    assert response.status_code == 204


def test_leave_workspace_as_last_admin_rejected(
    client: TestClient, user_auth_headers, workspace
):
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/me", headers=user_auth_headers
    )
    assert response.status_code == 400
    assert "Cannot leave as the last admin" in response.json()["message"]


def test_leave_workspace_last_member_deletes_workspace(
    client: TestClient, user, user_token, user_auth_headers, workspace, second_user
):
    """If the last member leaves, the workspace itself is deleted."""
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    member_token = login_user(client, email="user2@example.com")

    # Admin removes themselves from the workspace
    remove_response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/{user['id']}",
        headers=user_auth_headers,
    )
    assert remove_response.status_code == 200

    # Now only the regular member remains; they leave (last member)
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/me", headers=auth_header(member_token)
    )
    assert response.status_code == 204

    # Verify workspace is gone
    get_response = client.get(f"{wsprefix}/{workspace['id']}", headers=user_auth_headers)
    assert get_response.status_code == 404


@pytest.mark.parametrize(
    "token,expected_status",
    [
        pytest.param("outsider", 403, id="non_member"),
        pytest.param(None, 401, id="no_auth"),
    ],
)
def test_leave_workspace_auth_failures(
    client: TestClient, db_session, workspace, token, expected_status
):
    headers = None
    if token == "outsider":
        create_test_user(client, username="outsider", email="outsider@example.com")
        verify_user_in_db(db_session, "outsider@example.com")
        token = login_user(client, email="outsider@example.com")
        headers = auth_header(token)
    kwargs = {"headers": headers} if headers else {}
    response = client.delete(f"{wsprefix}/{workspace['id']}/members/me", **kwargs)
    assert response.status_code == expected_status


# ========================================================================================
# REMOVE MEMBER
# ========================================================================================


def test_remove_member_success(
    client: TestClient, user_token, user_auth_headers, workspace, second_user
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}",
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["num_of_members"] == 1


def test_remove_member_not_a_member(client: TestClient, user_auth_headers, workspace):
    stranger = create_test_user(
        client, username="stranger", email="stranger@example.com"
    )
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/{stranger['id']}",
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
def test_remove_member_auth_failures(
    client: TestClient,
    db_session,
    user_token,
    user_auth_headers,
    workspace,
    second_user,
    token,
    expected_status,
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    headers = None
    if token == "regular":
        regular_user = create_test_user(
            client, username="regular", email="regular@example.com"
        )
        add_workspace_member(client, user_token, workspace["id"], regular_user["id"])
        verify_user_in_db(db_session, "regular@example.com")
        regular_token = login_user(client, email="regular@example.com")
        headers = auth_header(regular_token)
    kwargs = {"headers": headers} if headers else {}
    response = client.delete(
        f"{wsprefix}/{workspace['id']}/members/{second_user['id']}", **kwargs
    )
    assert response.status_code == expected_status


def test_remove_member_nonexistent_workspace(client: TestClient, user_auth_headers):
    response = client.delete(f"{wsprefix}/99999/members/1", headers=user_auth_headers)
    assert_forbidden(response)

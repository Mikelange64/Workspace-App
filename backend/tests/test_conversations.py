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

convoprefix = "/api/workspaces"


# ========================================================================================
# FIXTURES / HELPERS
# ========================================================================================


def conversation_path(workspace_id: int, suffix: str = "") -> str:
    return f"{convoprefix}/{workspace_id}/conversations{suffix}"


def create_conversation(
    client: TestClient, token: str, workspace_id: int, title: str = "General"
) -> dict:
    response = client.post(
        conversation_path(workspace_id, "/"),
        json={"title": title},
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create conversation: {response.text}"
    return response.json()


def create_message(
    client: TestClient, token: str, workspace_id: int, conversation_id: int, content: str = "hi"
) -> dict:
    response = client.post(
        conversation_path(workspace_id, f"/{conversation_id}/messages"),
        json={"content": content},
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to send message: {response.text}"
    return response.json()


def promote_to_admin(client: TestClient, token: str, workspace_id: int, user_id: int) -> None:
    response = client.patch(
        f"/api/workspaces/{workspace_id}/members/{user_id}/admin", headers=auth_header(token)
    )
    assert response.status_code == 200, f"Failed to promote to admin: {response.text}"


def outsider_headers(client: TestClient, db_session) -> dict:
    create_test_user(client, username="outsider", email="outsider@example.com")
    verify_user_in_db(db_session, "outsider@example.com")
    token = login_user(client, email="outsider@example.com")
    return auth_header(token)


def assert_forbidden(response):
    assert response.status_code == 403


def assert_unauthorized(response):
    assert response.status_code == 401


@pytest.fixture
def conversation(client, user_token, workspace):
    """Create and return a conversation owned by the default user in their workspace."""
    return create_conversation(client, user_token, workspace["id"])


# ========================================================================================
# CREATE CONVERSATION
# ========================================================================================


def test_create_conversation_success(client: TestClient, user, user_auth_headers, workspace):
    response = client.post(
        conversation_path(workspace["id"], "/"),
        json={"title": "Design discussion"},
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Design discussion"
    assert data["workspace_id"] == workspace["id"]
    assert data["creator_id"] == user["id"]
    assert data["is_pinned"] is False
    assert data["is_archived"] is False
    assert data["last_message_at"] is None


def test_create_conversation_validation_error(client: TestClient, user_auth_headers, workspace):
    response = client.post(
        conversation_path(workspace["id"], "/"), json={"title": ""}, headers=user_auth_headers
    )
    assert response.status_code == 422


def test_create_conversation_non_member(client: TestClient, db_session, workspace):
    response = client.post(
        conversation_path(workspace["id"], "/"),
        json={"title": "Intruder"},
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_create_conversation_no_auth(client: TestClient, workspace):
    response = client.post(conversation_path(workspace["id"], "/"), json={"title": "No auth"})
    assert_unauthorized(response)


def test_create_conversation_nonexistent_workspace(client: TestClient, user_auth_headers):
    response = client.post(
        conversation_path(99999, "/"), json={"title": "Ghost"}, headers=user_auth_headers
    )
    assert_forbidden(response)


# ========================================================================================
# LIST CONVERSATIONS
# ========================================================================================


def test_list_conversations_empty(client: TestClient, user_auth_headers, workspace):
    response = client.get(conversation_path(workspace["id"], "/"), headers=user_auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_conversations_pinned_first(
    client: TestClient, user_auth_headers, user_token, workspace
):
    create_conversation(client, user_token, workspace["id"], title="First")
    second = create_conversation(client, user_token, workspace["id"], title="Second")

    client.patch(
        conversation_path(workspace["id"], f"/{second['id']}"),
        json={"is_pinned": True},
        headers=user_auth_headers,
    )

    response = client.get(conversation_path(workspace["id"], "/"), headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == second["id"]
    assert data[0]["is_pinned"] is True


def test_list_conversations_non_member(client: TestClient, db_session, workspace):
    response = client.get(
        conversation_path(workspace["id"], "/"), headers=outsider_headers(client, db_session)
    )
    assert_forbidden(response)


# ========================================================================================
# GET CONVERSATION
# ========================================================================================


def test_get_conversation_success(client: TestClient, user_auth_headers, conversation, workspace):
    response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}"), headers=user_auth_headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == conversation["id"]


def test_get_conversation_not_found(client: TestClient, user_auth_headers, workspace):
    response = client.get(
        conversation_path(workspace["id"], "/99999"), headers=user_auth_headers
    )
    assert response.status_code == 404


def test_get_conversation_cross_workspace_scoping(
    client: TestClient, user_token, user_auth_headers, workspace, conversation
):
    """A conversation must not be reachable through a different workspace's path,
    even for a user who is a member of both workspaces."""
    other_workspace = create_workspace(client, user_token, title="Other Workspace")
    response = client.get(
        conversation_path(other_workspace["id"], f"/{conversation['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# UPDATE CONVERSATION
# ========================================================================================


def test_update_conversation_as_creator_success(
    client: TestClient, user_auth_headers, conversation, workspace
):
    response = client.patch(
        conversation_path(workspace["id"], f"/{conversation['id']}"),
        json={"title": "Renamed"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


def test_update_conversation_pin_and_archive(
    client: TestClient, user_auth_headers, conversation, workspace
):
    response = client.patch(
        conversation_path(workspace["id"], f"/{conversation['id']}"),
        json={"is_pinned": True, "is_archived": True},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_pinned"] is True
    assert data["is_archived"] is True


def test_update_conversation_as_admin_success(
    client: TestClient,
    user_token,
    user_auth_headers,
    workspace,
    conversation,
    second_user,
    second_user_token,
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    promote_to_admin(client, user_token, workspace["id"], second_user["id"])

    response = client.patch(
        conversation_path(workspace["id"], f"/{conversation['id']}"),
        json={"title": "Renamed by admin"},
        headers=auth_header(second_user_token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed by admin"


def test_update_conversation_as_regular_member_forbidden(
    client: TestClient, user_token, workspace, conversation, second_user, second_user_token
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.patch(
        conversation_path(workspace["id"], f"/{conversation['id']}"),
        json={"title": "Hijacked"},
        headers=auth_header(second_user_token),
    )
    assert_forbidden(response)


def test_update_conversation_not_found(client: TestClient, user_auth_headers, workspace):
    response = client.patch(
        conversation_path(workspace["id"], "/99999"),
        json={"title": "Ghost"},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# DELETE CONVERSATION
# ========================================================================================


def test_delete_conversation_as_creator_success(
    client: TestClient, user_auth_headers, conversation, workspace
):
    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}"), headers=user_auth_headers
    )
    assert response.status_code == 204

    get_response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}"), headers=user_auth_headers
    )
    assert get_response.status_code == 404


def test_delete_conversation_as_regular_member_forbidden(
    client: TestClient, user_token, workspace, conversation, second_user, second_user_token
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}"),
        headers=auth_header(second_user_token),
    )
    assert_forbidden(response)


def test_delete_conversation_cascades_messages(
    client: TestClient, db_session, user_token, user_auth_headers, workspace, conversation
):
    message = create_message(client, user_token, workspace["id"], conversation["id"])

    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}"), headers=user_auth_headers
    )
    assert response.status_code == 204

    from app.models import Message as MessageModel

    assert db_session.get(MessageModel, message["id"]) is None


def test_delete_conversation_no_auth(client: TestClient, conversation, workspace):
    response = client.delete(conversation_path(workspace["id"], f"/{conversation['id']}"))
    assert_unauthorized(response)


# ========================================================================================
# SEND MESSAGE
# ========================================================================================


def test_send_message_success(
    client: TestClient, user, user_auth_headers, workspace, conversation
):
    response = client.post(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        json={"content": "Hello team"},
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello team"
    assert data["conversation_id"] == conversation["id"]
    assert data["sender_id"] == user["id"]


def test_send_message_empty_content_rejected(
    client: TestClient, user_auth_headers, workspace, conversation
):
    response = client.post(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        json={"content": ""},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


def test_send_message_non_member_forbidden(
    client: TestClient, db_session, workspace, conversation
):
    response = client.post(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        json={"content": "Intruder"},
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_send_message_conversation_not_found(client: TestClient, user_auth_headers, workspace):
    response = client.post(
        conversation_path(workspace["id"], "/99999/messages"),
        json={"content": "Ghost"},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


def test_send_message_cross_workspace_scoping(
    client: TestClient, user_token, user_auth_headers, workspace, conversation
):
    other_workspace = create_workspace(client, user_token, title="Other Workspace")
    response = client.post(
        conversation_path(other_workspace["id"], f"/{conversation['id']}/messages"),
        json={"content": "Should not land here"},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# LIST MESSAGES
# ========================================================================================


def test_list_messages_empty(client: TestClient, user_auth_headers, workspace, conversation):
    response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["total"] == 0


def test_list_messages_ordered_oldest_first(
    client: TestClient, user_auth_headers, user_token, workspace, conversation
):
    create_message(client, user_token, workspace["id"], conversation["id"], content="first")
    create_message(client, user_token, workspace["id"], conversation["id"], content="second")

    response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert [m["content"] for m in data["messages"]] == ["first", "second"]


def test_list_messages_non_member_forbidden(
    client: TestClient, db_session, workspace, conversation
):
    response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_list_messages_cross_workspace_scoping(
    client: TestClient, user_token, user_auth_headers, workspace, conversation
):
    other_workspace = create_workspace(client, user_token, title="Other Workspace")
    response = client.get(
        conversation_path(other_workspace["id"], f"/{conversation['id']}/messages"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# DELETE MESSAGE
# ========================================================================================


def test_delete_message_as_sender_success(
    client: TestClient, user_auth_headers, user_token, workspace, conversation
):
    message = create_message(client, user_token, workspace["id"], conversation["id"])
    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages/{message['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 204


def test_delete_message_as_admin_success(
    client: TestClient,
    user_token,
    workspace,
    conversation,
    second_user,
    second_user_token,
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    promote_to_admin(client, user_token, workspace["id"], second_user["id"])
    message = create_message(client, user_token, workspace["id"], conversation["id"])

    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages/{message['id']}"),
        headers=auth_header(second_user_token),
    )
    assert response.status_code == 204


def test_delete_message_as_other_member_forbidden(
    client: TestClient, user_token, workspace, conversation, second_user, second_user_token
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    message = create_message(client, user_token, workspace["id"], conversation["id"])

    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages/{message['id']}"),
        headers=auth_header(second_user_token),
    )
    assert_forbidden(response)


def test_delete_message_not_found(client: TestClient, user_auth_headers, workspace, conversation):
    response = client.delete(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages/99999"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# SURVIVAL ACROSS ACCOUNT DELETION (conversations/messages are workspace data, not personal)
# ========================================================================================


def test_conversation_survives_creator_account_deletion(
    client: TestClient, user_token, user_auth_headers, workspace, second_user, second_user_token
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    convo = create_conversation(client, second_user_token, workspace["id"])

    response = client.delete("/api/users/me", headers=auth_header(second_user_token))
    assert response.status_code == 204

    response = client.get(conversation_path(workspace["id"], f"/{convo['id']}"), headers=user_auth_headers)
    assert response.status_code == 200
    assert response.json()["creator_id"] is None


def test_message_survives_sender_account_deletion(
    client: TestClient, user_token, user_auth_headers, workspace, conversation, second_user, second_user_token
):
    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    message = create_message(client, second_user_token, workspace["id"], conversation["id"])

    response = client.delete("/api/users/me", headers=auth_header(second_user_token))
    assert response.status_code == 204

    response = client.get(
        conversation_path(workspace["id"], f"/{conversation['id']}/messages"),
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    sent = next(m for m in response.json()["messages"] if m["id"] == message["id"])
    assert sent["sender_id"] is None

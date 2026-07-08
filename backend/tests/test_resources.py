from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import (
    auth_header,
    create_task,
    create_test_user,
    login_user,
    verify_user_in_db,
)

resourceprefix = "/api/workspaces"


# ========================================================================================
# FIXTURES / HELPERS
# ========================================================================================


@pytest.fixture
def task(client, user_token, workspace):
    """Create and return a task owned by the default user in their workspace."""
    return create_task(client, user_token, workspace["id"])


@pytest.fixture
def fake_pdf_bytes() -> bytes:
    """Minimal bytes carrying just the PDF magic header - enough for filetype to sniff it."""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


def resource_path(workspace_id: int, task_id: int, suffix: str = "") -> str:
    return f"{resourceprefix}/{workspace_id}/tasks/{task_id}/resource{suffix}"


def create_link(
    client: TestClient,
    token: str,
    workspace_id: int,
    task_id: int,
    title: str = "My Link",
    url: str = "https://example.com",
) -> dict:
    response = client.post(
        resource_path(workspace_id, task_id, "/links"),
        json={"title": title, "url": url},
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create link: {response.text}"
    return response.json()


def create_note(
    client: TestClient,
    token: str,
    workspace_id: int,
    task_id: int,
    title: str = "My Note",
    content: str = "Some content",
) -> dict:
    response = client.post(
        resource_path(workspace_id, task_id, "/notes"),
        json={"title": title, "content": content},
        headers=auth_header(token),
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"
    return response.json()


def outsider_headers(client: TestClient, db_session) -> dict:
    """Create, verify, and log in a user with no relationship to the test workspace."""
    create_test_user(client, username="outsider", email="outsider@example.com")
    verify_user_in_db(db_session, "outsider@example.com")
    token = login_user(client, email="outsider@example.com")
    return auth_header(token)


def assert_forbidden(response):
    assert response.status_code == 403


def assert_unauthorized(response):
    assert response.status_code == 401


# ========================================================================================
# LINKS
# ========================================================================================


def test_create_link_success(client: TestClient, user_auth_headers, workspace, task):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/links"),
        json={"title": "Docs", "url": "https://example.com/docs"},
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Docs"
    assert data["url"] == "https://example.com/docs"
    assert "id" in data
    assert "created_at" in data


def test_create_link_invalid_url(client: TestClient, user_auth_headers, workspace, task):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/links"),
        json={"title": "Bad", "url": "not-a-url"},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


def test_create_link_non_member(client: TestClient, db_session, workspace, task):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/links"),
        json={"title": "Docs", "url": "https://example.com"},
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_create_link_no_auth(client: TestClient, workspace, task):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/links"),
        json={"title": "Docs", "url": "https://example.com"},
    )
    assert_unauthorized(response)


def test_get_link_success(client: TestClient, user_auth_headers, user_token, workspace, task):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == link["id"]


def test_get_link_not_found(client: TestClient, user_auth_headers, workspace, task):
    response = client.get(
        resource_path(workspace["id"], task["id"], "/links/99999"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


def test_get_note_through_link_getter_returns_404(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    """A note's id should not be retrievable through the link-typed getter."""
    note = create_note(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], f"/links/{note['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


def test_list_links_excludes_other_types(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    create_link(client, user_token, workspace["id"], task["id"], title="A")
    create_link(client, user_token, workspace["id"], task["id"], title="B")
    create_note(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], "/links"), headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {d["title"] for d in data} == {"A", "B"}


def test_update_link_partial(client: TestClient, user_auth_headers, user_token, workspace, task):
    link = create_link(client, user_token, workspace["id"], task["id"], title="Old")
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        json={"title": "New"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New"
    assert data["url"] == link["url"]


def test_update_link_url(client: TestClient, user_auth_headers, user_token, workspace, task):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        json={"url": "https://example.com/updated"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["url"] == "https://example.com/updated"


def test_update_link_empty_body_noop(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        json={},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["url"] == link["url"]
    assert response.json()["title"] == link["title"]


def test_update_link_not_found(client: TestClient, user_auth_headers, workspace, task):
    response = client.patch(
        resource_path(workspace["id"], task["id"], "/links/99999"),
        json={"title": "Ghost"},
        headers=user_auth_headers,
    )
    assert response.status_code == 404


def test_update_link_by_other_workspace_member_allowed(
    client: TestClient, user_token, workspace, task, second_user, second_user_token
):
    """Any workspace member can edit shared resources - there's no creator-only restriction."""
    from tests.auth_helpers import add_workspace_member

    add_workspace_member(client, user_token, workspace["id"], second_user["id"])
    link = create_link(client, user_token, workspace["id"], task["id"], title="Original")
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        json={"title": "Edited by teammate"},
        headers=auth_header(second_user_token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Edited by teammate"


# ========================================================================================
# NOTES
# ========================================================================================


def test_create_note_success(client: TestClient, user_auth_headers, workspace, task):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/notes"),
        json={"title": "Meeting Notes", "content": "Discussed X and Y."},
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Meeting Notes"
    assert data["content"] == "Discussed X and Y."


def test_create_note_empty_content_allowed(client: TestClient, user_auth_headers, workspace, task):
    """NoteCreate has no min_length on content, matching TaskCreate's own convention."""
    response = client.post(
        resource_path(workspace["id"], task["id"], "/notes"),
        json={"title": "Empty", "content": ""},
        headers=user_auth_headers,
    )
    assert response.status_code == 201


def test_get_note_success(client: TestClient, user_auth_headers, user_token, workspace, task):
    note = create_note(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], f"/notes/{note['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == note["content"]


def test_list_notes_excludes_other_types(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    create_note(client, user_token, workspace["id"], task["id"], title="A")
    create_link(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], "/notes"), headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_update_note_content(client: TestClient, user_auth_headers, user_token, workspace, task):
    note = create_note(client, user_token, workspace["id"], task["id"])
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/notes/{note['id']}"),
        json={"content": "Updated content"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


def test_update_note_empty_content_rejected(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    """Unlike creation, NoteUpdate requires min_length=1 when content is explicitly sent."""
    note = create_note(client, user_token, workspace["id"], task["id"])
    response = client.patch(
        resource_path(workspace["id"], task["id"], f"/notes/{note['id']}"),
        json={"content": ""},
        headers=user_auth_headers,
    )
    assert response.status_code == 422


def test_get_link_through_note_getter_returns_404(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], f"/notes/{link['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 404


# ========================================================================================
# FILES
# ========================================================================================


def test_upload_file_success(
    client: TestClient, user_auth_headers, workspace, task, mocked_s3, fake_pdf_bytes
):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("report.pdf", fake_pdf_bytes, "application/pdf")},
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "report.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_path"].startswith("https://")


def test_upload_file_too_large(client: TestClient, user_auth_headers, workspace, task, mocked_s3):
    from app.config import settings

    oversized = b"%PDF-1.4\n" + b"0" * (settings.max_file_upload_size_bytes + 1)
    response = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("big.pdf", BytesIO(oversized), "application/pdf")},
        headers=user_auth_headers,
    )
    assert response.status_code == 400
    assert "File too large" in response.json()["message"]


def test_upload_file_unrecognizable_content_rejected(
    client: TestClient, user_auth_headers, workspace, task, mocked_s3
):
    """Plain text has no magic bytes for filetype to sniff, so it can never pass validation."""
    response = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("note.txt", b"just plain text, no magic bytes here", "text/plain")},
        headers=user_auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid file" in response.json()["message"]


def test_upload_file_recognized_but_disallowed_type_rejected(
    client: TestClient, user_auth_headers, workspace, task, mocked_s3
):
    """A real, sniffable format (PNG) that isn't in ALLOWED_MIME_TYPES should still be rejected."""
    png_header = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    response = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("image.png", png_header, "image/png")},
        headers=user_auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid file" in response.json()["message"]


def test_upload_file_non_member(client: TestClient, db_session, workspace, task, mocked_s3, fake_pdf_bytes):
    response = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("report.pdf", fake_pdf_bytes, "application/pdf")},
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_list_files_excludes_other_types(
    client: TestClient, user_auth_headers, user_token, workspace, task, mocked_s3, fake_pdf_bytes
):
    client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("report.pdf", fake_pdf_bytes, "application/pdf")},
        headers=auth_header(user_token),
    )
    create_link(client, user_token, workspace["id"], task["id"])
    response = client.get(
        resource_path(workspace["id"], task["id"], "/files"), headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "report.pdf"


def test_delete_file_removes_from_s3(
    client: TestClient, user_auth_headers, workspace, task, mocked_s3, fake_pdf_bytes
):
    from app.config import settings

    upload = client.post(
        resource_path(workspace["id"], task["id"], "/files"),
        files={"file": ("report.pdf", fake_pdf_bytes, "application/pdf")},
        headers=user_auth_headers,
    ).json()

    response = client.delete(
        resource_path(workspace["id"], task["id"], f"/{upload['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 204

    objects = mocked_s3.list_objects_v2(Bucket=settings.s3_bucket_name).get("Contents", [])
    assert objects == []


# ========================================================================================
# CROSS-CUTTING: DELETE (any type) + unified list
# ========================================================================================


def test_delete_link_success(client: TestClient, user_auth_headers, user_token, workspace, task):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.delete(
        resource_path(workspace["id"], task["id"], f"/{link['id']}"),
        headers=user_auth_headers,
    )
    assert response.status_code == 204

    get_response = client.get(
        resource_path(workspace["id"], task["id"], f"/links/{link['id']}"),
        headers=user_auth_headers,
    )
    assert get_response.status_code == 404


def test_delete_resource_non_member_forbidden(
    client: TestClient, db_session, user_token, workspace, task
):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.delete(
        resource_path(workspace["id"], task["id"], f"/{link['id']}"),
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)


def test_delete_resource_no_auth(client: TestClient, user_token, workspace, task):
    link = create_link(client, user_token, workspace["id"], task["id"])
    response = client.delete(resource_path(workspace["id"], task["id"], f"/{link['id']}"))
    assert_unauthorized(response)


def test_list_resources_mixed_types(
    client: TestClient, user_auth_headers, user_token, workspace, task
):
    create_link(client, user_token, workspace["id"], task["id"], title="Link")
    create_note(client, user_token, workspace["id"], task["id"], title="Note")
    response = client.get(
        resource_path(workspace["id"], task["id"], "/"), headers=user_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {d["type"] for d in data} == {"LINK", "NOTE"}


def test_list_resources_empty(client: TestClient, user_auth_headers, workspace, task):
    response = client.get(
        resource_path(workspace["id"], task["id"], "/"), headers=user_auth_headers
    )
    assert response.status_code == 200
    assert response.json() == []


def test_list_resources_non_member(client: TestClient, db_session, workspace, task):
    response = client.get(
        resource_path(workspace["id"], task["id"], "/"),
        headers=outsider_headers(client, db_session),
    )
    assert_forbidden(response)

from typing import Annotated

from botocore.exceptions import ClientError
from fastapi import APIRouter, status, HTTPException, UploadFile, Depends
from PIL import UnidentifiedImageError
from sqlalchemy import select

from app.database import DbSession
from app.config import settings
from app.dependencies import require_membership
from app.models import Resource, ResourceType, WorkspaceMember
from app.utils import (
    process_file,
    upload_file,
    delete_file,
    get_resource_by_id,
    normalize_image,
    fetch_oembed_thumbnail,
)
from app.schemas import (
    LinkCreate,
    LinkResponse,
    LinkUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    FileResponse,
    ResourceSummary,
)


router = APIRouter(prefix="/{workspace_id}/tasks/{task_id}/resource", tags=["resources"])


def _get_typed_resource(resource_id: int, expected_type: ResourceType, db: DbSession) -> Resource:
    resource = get_resource_by_id(resource_id, db)
    if resource.type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    return resource


def _save_resource(resource: Resource, db: DbSession) -> Resource:
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def _list_by_type(task_id: int, resource_type: ResourceType, db: DbSession) -> list[Resource]:
    return db.execute(
        select(Resource)
        .where(Resource.task_id == task_id, Resource.type == resource_type)
        .order_by(Resource.created_at)
    ).scalars().all() # type: ignore[return-value]


@router.get( "/", response_model=list[ResourceSummary], dependencies=[Depends(require_membership)])
def list_resources(task_id: int, db: DbSession):
    return db.execute(
        select(Resource).where(Resource.task_id == task_id).order_by(Resource.created_at)
    ).scalars().all()


# =============================================== LINKS ======================================================

@router.post("/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def add_link(
    task_id: int,
    data: LinkCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    new_link = Resource(
        task_id       = task_id,
        created_by    = member.user_id,
        type          = ResourceType.LINK,
        title         = data.title,
        url           = str(data.url),
        thumbnail_url = fetch_oembed_thumbnail(str(data.url)),
    )
    return _save_resource(new_link, db)


@router.get("/links", response_model=list[LinkResponse], dependencies=[Depends(require_membership)]
)
def list_links(task_id: int, db: DbSession):
    return _list_by_type(task_id, ResourceType.LINK, db)


@router.get("/links/{link_id}", response_model=LinkResponse, dependencies=[Depends(require_membership)])
def get_link(link_id: int, db: DbSession):
    return _get_typed_resource(link_id, ResourceType.LINK, db)


@router.patch("/links/{link_id}", response_model=LinkResponse, dependencies=[Depends(require_membership)])
def update_link(link_id: int, data: LinkUpdate, db: DbSession):
    resource = _get_typed_resource(link_id, ResourceType.LINK, db)

    update = data.model_dump(exclude_unset=True)
    for field, value in update.items():
        # model_dump() keeps url as an HttpUrl object, not str; resource.url is a plain String column
        setattr(resource, field, str(value) if field == "url" else value)

    if "url" in update:
        resource.thumbnail_url = fetch_oembed_thumbnail(resource.url)

    db.commit()
    db.refresh(resource)
    return resource


# =============================================== NOTES ======================================================

@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def add_note(
    task_id: int,
    data: NoteCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    new_note = Resource(
        task_id    = task_id,
        created_by = member.user_id,
        type       = ResourceType.NOTE,
        title      = data.title,
        content    = data.content,
    )
    return _save_resource(new_note, db)


@router.get("/notes", response_model=list[NoteResponse], dependencies=[Depends(require_membership)])
def list_notes(task_id: int, db: DbSession):
    return _list_by_type(task_id, ResourceType.NOTE, db)


@router.get("/notes/{note_id}", response_model=NoteResponse, dependencies=[Depends(require_membership)])
def get_note(note_id: int, db: DbSession):
    return _get_typed_resource(note_id, ResourceType.NOTE, db)


@router.patch("/notes/{note_id}", response_model=NoteResponse, dependencies=[Depends(require_membership)])
def update_note(note_id: int, data: NoteUpdate, db: DbSession):
    resource = _get_typed_resource(note_id, ResourceType.NOTE, db)

    update = data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)
    return resource


# =============================================== FILES ======================================================

@router.get("/files", response_model=list[FileResponse], dependencies=[Depends(require_membership)])
def list_files(task_id: int, db: DbSession):
    return _list_by_type(task_id, ResourceType.FILE, db)


@router.post("/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def upload_resource_file(
    task_id: int,
    file: UploadFile,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    content = file.file.read()

    if len(content) > settings.max_file_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_file_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        processed_bytes, file_key, mime = process_file(content, file.filename)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file. Please upload a valid file type (PDF, DOCX, ODT, PPT, PPTX, XLS, XLSX, JPEG, PNG, GIF, WEBP, TXT)",
        ) from err

    if mime.startswith("image/"):
        try:
            processed_bytes = normalize_image(processed_bytes, mime)
        except (UnidentifiedImageError, OSError) as err:
            # Magic bytes matched, but Pillow couldn't fully decode it (e.g.
            # truncated/corrupt data past the header).
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file. Please upload a valid image.",
            ) from err

    try:
        upload_file(processed_bytes, file_key, mime)
    except ClientError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to upload file, please try again.",
        ) from err

    new_resource = Resource(
        task_id    = task_id,
        created_by = member.user_id,
        type       = ResourceType.FILE,
        title      = file.filename,
        file_key   = file_key,
        mime_type  = mime,
    )
    return _save_resource(new_resource, db)


# =============================================== DELETE (any type) ==========================================

@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_membership)],
)
def delete_resource(resource_id: int, db: DbSession):
    resource = get_resource_by_id(resource_id, db)

    if resource.type == ResourceType.FILE:
        delete_file(resource.file_key)

    db.delete(resource)
    db.commit()

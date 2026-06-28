from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy import update as sql_update

from app.auth import CurrentUser
from app.database import DbSession
from app.models import Folder, Workspace
from app.schemas import FolderCreate, FolderResponse, FolderUpdate

router = APIRouter(tags=["folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(data: FolderCreate, current_user: CurrentUser, db: DbSession):
    folder = Folder(owner_id=current_user.id, name=data.name, color=data.color)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.get("", response_model=list[FolderResponse])
def list_folders(current_user: CurrentUser, db: DbSession):
    folders = (
        db.execute(select(Folder).where(Folder.owner_id == current_user.id))
        .scalars().all()
    )
    return folders


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(folder_id: int, data: FolderUpdate, current_user: CurrentUser, db: DbSession):
    folder = _get_owned_folder(folder_id, current_user.id, db)

    update = data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(folder, field, value)

    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: int, current_user: CurrentUser, db: DbSession):
    folder = _get_owned_folder(folder_id, current_user.id, db)

    db.execute(
        sql_update(Workspace)
        .where(Workspace.folder_id == folder_id)
        .values(folder_id=None)
    )
    db.delete(folder)
    db.commit()


def _get_owned_folder(folder_id: int, user_id: int, db: DbSession) -> Folder:
    folder = db.execute(
        select(Folder).where(Folder.id == folder_id)
    ).scalars().first()

    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    if folder.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your folder")

    return folder

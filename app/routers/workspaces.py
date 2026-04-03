from fastapi import APIRouter, Depends, status, HTTPException

from typing import Annotated

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.users import User
from app.models.workspaces import Workspace
from app.models.association import WorkspaceMember

from app.schemas.workspaces import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from app.schemas.tasks import TaskResponse

from app.database import get_db
from app.auth import CurrentUser
from app.utility import require_admin, require_membership, get_target_membership

router = APIRouter()


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
        current_user: CurrentUser,
        workspace: WorkspaceCreate,
        db: Annotated[Session, Depends(get_db)]
):
    new_workspace = Workspace(
        creator_id=current_user.id,
        title=workspace.title,
        description=workspace.description,
        max_number=workspace.max_number,
        due_date=workspace.due_date,
    )

    new_member = WorkspaceMember(
        user_id=current_user.id,
        workspace_id=new_workspace.id,
        role="admin"
    )

    db.add(new_workspace)
    db.add(new_member)
    db.commit()
    db.refresh(new_workspace)

    return new_workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
            select(Workspace).options(
                joinedload(Workspace.members),
                joinedload(Workspace.tasks)
            ).where(Workspace.id == workspace_id)
    )
    workspace = result.scalars().first()

    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return workspace


@router.get("/tasks/{workspace_id}", response_model=list[TaskResponse])
def get_tasks(
        workspace_id: int,
        current_user : Annotated[WorkspaceMember, Depends(require_membership)],
        db: Annotated[Session, Depends(get_db)]
):
    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    return workspace.tasks


@router.get("/members/{workspace_id}/", response_model=list[TaskResponse])
def get_members(
        workspace_id: int,
        current_user : Annotated[WorkspaceMember, Depends(require_membership)],
        db: Annotated[Session, Depends(get_db)]
):
    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    return workspace.members


@router.patch("/members/add/{workspace_id}/{user_id}", response_model=WorkspaceResponse)
def add_user(
        workspace_id: int,
        user_id: int,
        current_user: Annotated[WorkspaceMember, Depends(require_admin)],
        db: Annotated[Session, Depends(get_db)]
):
    target_user = db.execute(select(User).where(User.id == user_id)).scalars().first()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_member = get_target_membership(workspace_id, user_id, db)

    if is_member:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already in the workspace")

    new_member = WorkspaceMember(
        user_id=target_user.id,
        workspace_id=workspace_id
    )
    db.add(new_member)
    db.commit()

    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    return workspace


@router.patch("/members/remove/{workspace_id}/{user_id}", response_model=WorkspaceResponse)
def remove_user(
        workspace_id : int,
        user_id      : int,
        current_user : Annotated[WorkspaceMember, Depends(require_admin)],
        db           : Annotated[Session, Depends(get_db)]
):
    member = get_target_membership(workspace_id, user_id, db)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of this workspace")
    db.delete(member)
    db.commit()

    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    return workspace


@router.patch("/members/make-admin/{workspace_id}/{user_id}", response_model=WorkspaceResponse)
def make_admin(
        workspace_id : int,
        user_id      : int,
        current_user : Annotated[WorkspaceMember, Depends(require_admin)],
        db           : Annotated[Session, Depends(get_db)]
):
    member = get_target_membership(workspace_id, user_id, db)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of this workspace")

    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    if member.role == "admin":
        return workspace

    member.role = "admin"
    db.commit()
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace_partial(
        workspace_id: int,
        current_user: Annotated[WorkspaceMember, Depends(require_membership)],
        workspace_data: WorkspaceUpdate,
        db: Annotated[Session, Depends(get_db)]
):
    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()

    update = workspace_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return workspace


@router.put("/{workspace_id}/", response_model=WorkspaceResponse)
def update_workspace_full(
        workspace_id: int,
        current_user: Annotated[WorkspaceMember, Depends(require_membership)],
        workspace_data: WorkspaceCreate,
        db: Annotated[Session, Depends(get_db)]
):
    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()

    workspace.title = workspace_data.title
    workspace.description = workspace_data.description
    workspace.max_number = workspace_data.max_number
    workspace.due_date = workspace_data.due_date

    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
        workspace_id: int,
        admin : Annotated[WorkspaceMember, Depends(require_admin)],
        db: Annotated[Session, Depends(get_db)]
):
    workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
    db.delete(workspace)
    db.commit()
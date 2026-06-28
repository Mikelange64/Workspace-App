from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.auth import CurrentUser
from app.database import DbSession
from app.dependencies import get_target_membership, require_admin, require_membership
from app.utils import get_workspace_by_id

from app.models import User, Workspace, WorkspaceMember
from app.schemas import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceMemberPublic,
    PaginatedWorkspaceResponse,
    UserPublic,
)

router = APIRouter(tags=["workspaces"])


# ========================================================================================
# WORKSPACE CRUD
# ========================================================================================


@router.get("", response_model=PaginatedWorkspaceResponse)
def get_my_workspaces(
    current_user: CurrentUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 20,
):
    base = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0

    workspaces = (
        db.execute(
            base
            .options(joinedload(Workspace.members), joinedload(Workspace.tasks))
            .offset(skip)
            .limit(limit)
        )
        .scalars().unique().all()
    )

    workspace_ids = [ws.id for ws in workspaces]
    role_map = {
        ws_id: role
        for ws_id, role in db.execute(
            select(WorkspaceMember.workspace_id, WorkspaceMember.role).where(
                WorkspaceMember.workspace_id.in_(workspace_ids),
                WorkspaceMember.user_id == current_user.id,
            )
        ).all()
    }

    return PaginatedWorkspaceResponse(
        workspaces=[
            WorkspaceResponse.model_validate(ws).model_copy(
                update={"current_user_role": role_map.get(ws.id)}
            )
            for ws in workspaces
        ],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(current_user: CurrentUser, workspace: WorkspaceCreate, db: DbSession):
    new_workspace = Workspace(
        creator_id=current_user.id,
        title=workspace.title,
        description=workspace.description,
        max_number=workspace.max_number,
        due_date=workspace.due_date,
    )
    db.add(new_workspace)
    db.flush()

    new_member = WorkspaceMember(user_id=current_user.id, workspace_id=new_workspace.id, role="admin")
    db.add(new_member)
    db.commit()
    db.refresh(new_workspace)

    return WorkspaceResponse.model_validate(new_workspace).model_copy(update={"current_user_role": "admin"})


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, current_user: CurrentUser, db: DbSession):
    workspace = db.execute(
        select(Workspace)
        .options(joinedload(Workspace.members), joinedload(Workspace.tasks))
        .where(Workspace.id == workspace_id)
    ).scalars().first()

    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    role = db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    ).scalar()

    return WorkspaceResponse.model_validate(workspace).model_copy(update={"current_user_role": role})


@router.patch(
    "/{workspace_id}", response_model=WorkspaceResponse, dependencies=[Depends(require_membership)]
)
def update_workspace_partial(workspace_id: int, workspace_data: WorkspaceUpdate, db: DbSession):
    workspace = get_workspace_by_id(workspace_id, db)

    update = workspace_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete(
    "/{workspace_id}/", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)]
)
def delete_workspace(workspace_id: int, current_user: CurrentUser, db: DbSession):
    workspace = get_workspace_by_id(workspace_id, db)
    if workspace.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace creator can delete it")
    db.delete(workspace)
    db.commit()


# ========================================================================================
# MEMBER MANAGEMENT
# ========================================================================================


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberPublic],
    dependencies=[Depends(require_membership)],
)
def get_members(workspace_id: int, db: DbSession):
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    ).all()
    return [
        WorkspaceMemberPublic(id=user.id, username=user.username, image_path=user.image_path, role=membership.role)
        for membership, user in rows
    ]


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_admin)],
)
def add_user(workspace_id: int, user_id: int, db: DbSession):
    if get_target_membership(workspace_id, user_id, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already in the workspace")

    db.add(WorkspaceMember(user_id=user_id, workspace_id=workspace_id))
    db.commit()

    return get_workspace_by_id(workspace_id, db)


@router.patch(
    "/{workspace_id}/members/{user_id}/admin",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_admin)],
)
def make_admin(workspace_id: int, user_id: int, db: DbSession):
    member = get_target_membership(workspace_id, user_id, db)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not a member of this workspace")

    workspace = get_workspace_by_id(workspace_id, db)
    if member.role == "admin":
        return workspace

    member.role = "admin"
    db.commit()
    return workspace


@router.delete("/{workspace_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_workspace(
    workspace_id: int,
    db: DbSession,
    membership: Annotated[WorkspaceMember, Depends(require_membership)],
):
    if membership.role == "admin":
        admin_count = db.execute(
            select(func.count()).where(
                WorkspaceMember.workspace_id == membership.workspace_id,
                WorkspaceMember.role == "admin",
            )
        ).scalar()
        if admin_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave as the last admin, promote someone first",
            )

    db.delete(membership)
    db.commit()

    member_count = db.execute(
        select(func.count()).where(WorkspaceMember.workspace_id == workspace_id)
    ).scalar()

    if member_count == 0:
        workspace = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalars().first()
        db.delete(workspace)
        db.commit()


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def remove_user(workspace_id: int, user_id: int, db: DbSession):
    member = get_target_membership(workspace_id, user_id, db)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not a member of this workspace")

    db.delete(member)
    db.commit()

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.auth import CurrentUser
from app.database import DbSession
from app.dependencies import get_target_membership, require_admin, require_membership
from app.utils import get_workspace_by_id

from app.models import Workspace, WorkspaceMember
from app.schemas import (
    UserPublic,
    WorkspaceCreate, 
    WorkspaceResponse, 
    WorkspaceUpdate,
)

router = APIRouter(tags=["workspaces"]) 


# ========================================================================================
# CRUD OPERATIONS ON THE WORKSPACE ITSELF
# ========================================================================================


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    current_user : CurrentUser,
    workspace    : WorkspaceCreate,
    db           : DbSession,
):
    new_workspace = Workspace(
        creator_id=current_user.id,
        title=workspace.title,
        description=workspace.description,
        max_number=workspace.max_number,
        due_date=workspace.due_date,
    )
    
    db.add(new_workspace)
    db.flush() # flush is for when the object is not yet in the db
    
    new_member = WorkspaceMember(
        user_id=current_user.id, workspace_id=new_workspace.id, role="admin"
    )

    db.add(new_workspace)
    db.add(new_member)
    db.commit()
    db.refresh(new_workspace)

    return new_workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: DbSession):
    result = db.execute(
        select(Workspace)
        .options(joinedload(Workspace.members), joinedload(Workspace.tasks))
        .where(Workspace.id == workspace_id)
    )
    workspace = result.scalars().first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    return workspace
    

@router.patch(
    "/{workspace_id}", response_model=WorkspaceResponse, dependencies=[Depends(require_membership)]
)
def update_workspace_partial(
    workspace_id   : int,
    workspace_data : WorkspaceUpdate,
    db             : DbSession,
) -> Workspace | None:
    workspace = get_workspace_by_id(workspace_id, db)
    
    update = workspace_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(workspace, field, value)
    
    db.commit()
    db.refresh(workspace)
    return workspace


@router.put(
    "/{workspace_id}/", response_model=WorkspaceResponse, dependencies=[Depends(require_membership)]
)
def update_workspace_full(
    workspace_id   : int,
    workspace_data : WorkspaceCreate,
    db             : DbSession,
) -> Workspace | None:
    workspace = get_workspace_by_id(workspace_id, db)
    
    update = workspace_data.model_dump()
    for field, value in update.items():
        setattr(workspace, field, value)
    
    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete(
    "/{workspace_id}/", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)]
)
def delete_workspace(
    workspace_id : int,
    db           : DbSession,
) -> None :
    workspace = get_workspace_by_id(workspace_id, db)
    db.delete(workspace)
    db.commit()


# ========================================================================================
# OPERATIONS ON WORKSPACE SUB-RESOURCES
# ========================================================================================


@router.get(
    "/{workspace_id}/members", response_model=list[UserPublic], dependencies=[Depends(require_membership)]
)
def get_members(
    workspace_id : int,
    db           : DbSession,
):
    workspace = get_workspace_by_id(workspace_id, db)
    return workspace.members


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceResponse)
def add_user(
    user_id      : int,
    workspace_id : int,
    db           : DbSession,
    current_user : Annotated[WorkspaceMember, Depends(require_admin)],
):
    is_member = get_target_membership(workspace_id, user_id, db)

    if is_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already in the workspace"
        )

    new_member = WorkspaceMember(user_id=user_id, workspace_id=workspace_id)
    db.add(new_member)
    db.commit()

    workspace = get_workspace_by_id(workspace_id, db)
    return workspace


@router.patch("/{workspace_id}/members/{user_id}/admin", response_model=WorkspaceResponse)
def make_admin(
    workspace_id : int,
    user_id      : int,
    db           : DbSession,
    current_user : Annotated[WorkspaceMember, Depends(require_admin)],
):
    member = get_target_membership(workspace_id, user_id, db)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )

    workspace = get_workspace_by_id(workspace_id, db)

    if member.role == "admin":
        return workspace

    member.role = "admin"
    db.commit()

    return workspace


@router.delete("/{workspace_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_workspace(
    workspace_id : int,
    db           : DbSession,
    membership   : Annotated[WorkspaceMember, Depends(require_membership)],
):
    if membership.role == "admin" :
        admin_count = db.execute(
            select(func.count()).where(
                WorkspaceMember.workspace_id == membership.workspace_id,
                WorkspaceMember.role == "admin"
            )
        ).scalar()

        if admin_count == 1 :
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST, 
                detail = "Cannot leave as the last admin, promote someone first"
            )

    db.delete(membership)
    db.commit()

    member_count = db.execute(
        select(func.count()).where(
            WorkspaceMember.workspace_id == workspace_id
        )
    ).scalar()
    
    if member_count == 0:
        workspace = db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        ).scalars().first()
        
        db.delete(workspace)
        db.commit()
        
        
@router.delete("/{workspace_id}/members/{user_id}", response_model=WorkspaceResponse)
def remove_user(
    workspace_id : int,
    user_id      : int,
    db           : DbSession,
    current_user : Annotated[WorkspaceMember, Depends(require_admin)],
):
    member = get_target_membership(workspace_id, user_id, db)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )

    db.delete(member)
    db.commit()

    workspace = get_workspace_by_id(workspace_id, db)
    return workspace

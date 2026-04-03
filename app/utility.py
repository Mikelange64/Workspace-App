from fastapi import Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Annotated

from app.models.association import WorkspaceMember
from app.models.users import User
from app.models.workspaces import Workspace
from app.auth import CurrentUser
from app.database import get_db


def require_admin(
        workspace_id: int,
        current_user: CurrentUser,
        db: Annotated[Session, Depends(get_db)]
):
    query = select(WorkspaceMember).where(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.role == "admin"
    )
    is_admin = db.execute(query).scalar().first()

    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can perform this action")

    return is_admin


def require_membership(
        workspace_id : int,
        current_user: CurrentUser,
        db: Annotated[Session, Depends(get_db)]
):
    query = select(WorkspaceMember).where(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.workspace_id == workspace_id,
    )
    is_member = db.execute(query).scalars().first()

    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of this workspace")

    return is_member


def get_target_membership(
        workspace_id : int,
        user_id : int,
        db: Annotated[Session, Depends(get_db)]
):
    return db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id
        )
    ).scalars().first()
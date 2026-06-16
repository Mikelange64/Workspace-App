from fastapi import HTTPException, status

from sqlalchemy import select

from app.models.workspaces import Workspace
from app.database import DbSession
from app.models import Task, User


def get_user_by_id(user_id: int,  db: DbSession) -> User:
    user = (
        db.execute(select(User).where(User.id == user_id)).scalars().first()
    )

    if not user :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "User not found"
        )
    
    return user


def get_task_by_id(task_id: int, db: DbSession) -> Task: 
    task = (
        db.execute(select(Task).where(Task.id == task_id)).scalars().first()
    )

    if not task :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "Task not found"
        )

    return task


def get_workspace_by_id(workspace_id: int,  db: DbSession) -> Workspace : 
    workspace = (
        db.execute(select(Workspace).where(Workspace.id == workspace_id))
        .scalars().first()
    )

    if not workspace :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "Workspace not found"
        )

    return workspace
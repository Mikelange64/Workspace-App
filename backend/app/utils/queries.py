from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.workspaces import Workspace
from app.database import DbSession
from app.models import Conversation, Resource, Task, User


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


def get_resource_by_id(resource_id: int, db: DbSession) -> Resource:
    resource = (
        db.execute(select(Resource).where(Resource.id == resource_id)).scalars().first()
    )

    if not resource :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "Resource not found"
        )

    return resource


def get_conversation_by_id(conversation_id: int, workspace_id: int, db: DbSession) -> Conversation:
    # scoped to workspace_id so a member of one workspace can't reach another
    # workspace's conversation by guessing its id
    conversation = (
        db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        .scalars().first()
    )

    if not conversation :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "Conversation not found"
        )

    return conversation


def get_workspace_by_id(workspace_id: int,  db: DbSession) -> Workspace :
    workspace = (
        db.execute(
            select(Workspace)
            .options(joinedload(Workspace.members), joinedload(Workspace.tasks))
            .where(Workspace.id == workspace_id)
        )
        .scalars().first()
    )

    if not workspace :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, detail = "Workspace not found"
        )

    return workspace
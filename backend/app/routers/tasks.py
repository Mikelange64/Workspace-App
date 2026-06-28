from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import DbSession
from app.models import Task, WorkspaceMember
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.dependencies import (
    get_target_membership,
    require_admin,
    require_membership,
)
from app.utils import get_task_by_id


router = APIRouter(prefix="/{workspace_id}/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    workspace_id: int,
    task: TaskCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    new_task = Task(
        title=task.title,
        content=task.content,
        creator_id=member.user_id,
        owner_id=member.user_id,
        workspace_id=workspace_id,
        due_date=task.due_date,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_membership)],
)
def get_task(
    task_id: int,
    workspace_id: int,
    db: DbSession,
):
    task = get_task_by_id(task_id, db)
    return task


@router.patch(
    "/{task_id}/",
    response_model=TaskResponse,
    dependencies=[Depends(require_membership)],
)
def update_task_partial(
    task_id: int,
    workspace_id: int,
    task_data: TaskUpdate,
    db: DbSession,
):
    task = get_task_by_id(task_id, db)

    update = task_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_task(
    task_id: int,
    workspace_id: int,
    db: DbSession,
):
    task = get_task_by_id(task_id, db)
    db.delete(task)
    db.commit()


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    workspace_id: int,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = get_task_by_id(task_id, db)
    if task.owner_id != member.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the task owner can mark it complete",
        )
    task.is_completed = not task.is_completed
    db.commit()
    db.refresh(task)
    return task


@router.patch(
    "/{task_id}/owner",
    response_model=TaskResponse,
)
def reassign_task(
    task_id: int,
    workspace_id: int,
    user_id: Annotated[int, Query()],
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = get_task_by_id(task_id, db)
    if task.owner_id != member.user_id and member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the task owner or an admin can reassign this task",
        )

    target = get_target_membership(workspace_id, user_id, db)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this workspace",
        )

    task.owner_id = target.user_id
    db.commit()
    db.refresh(task)
    return task

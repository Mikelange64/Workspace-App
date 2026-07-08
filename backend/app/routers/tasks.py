from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from app.database import DbSession
from app.models import Task, WorkspaceMember
from app.schemas import (
    PaginatedTaskResponse,
    TaskCreate,
    TaskFullUpdate,
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
    "/", response_model=PaginatedTaskResponse, dependencies=[Depends(require_membership)]
)
def list_tasks(
    workspace_id: int,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    base = select(Task).where(Task.workspace_id == workspace_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
    tasks = db.execute(base.offset(skip).limit(limit)).scalars().all()

    return PaginatedTaskResponse(
        tasks=tasks,
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )


@router.get(
    "/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_membership)]
)
def get_task(task_id: int, db: DbSession):
    task = get_task_by_id(task_id, db)
    return task


@router.patch(
    "/{task_id}/", response_model=TaskResponse, dependencies=[Depends(require_membership)]
)
def update_task_partial(task_id: int, task_data: TaskUpdate, db: DbSession):
    task = get_task_by_id(task_id, db)

    update = task_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task_full(
    task_id: int,
    task_data: TaskFullUpdate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = get_task_by_id(task_id, db)
    if task.owner_id != member.user_id and member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to fully update this task",
        )

    task.title = task_data.title
    task.content = task_data.content
    task.due_date = task_data.due_date

    db.commit()
    db.refresh(task)
    return task


@router.delete(
    "/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)]
)
def delete_task(task_id: int, db: DbSession):
    task = get_task_by_id(task_id, db)
    db.delete(task)
    db.commit()


@router.patch(
    "/{task_id}/complete", response_model=TaskResponse, dependencies=[Depends(require_membership)]
)
def complete_task(task_id: int, db: DbSession):
    task = get_task_by_id(task_id, db)
    task.is_completed = not task.is_completed
    task.completed_at = datetime.now(UTC) if task.is_completed else None
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/owner", response_model=TaskResponse,)
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )

    task.owner_id = target.user_id
    db.commit()
    db.refresh(task)
    return task
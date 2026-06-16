from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func

from app.database import DbSession
from app.models import Task, Workspace, WorkspaceMember
from app.schemas import (
    TaskCreate,
    TaskMove,
    TaskResponse,
    TaskUpdate,
    WorkspaceResponse,
    PaginatedTaskResponse
)
from app.dependencies import (
    get_target_membership,
    require_admin,
    require_membership,
)
from app.utils import get_task_by_id, get_user_by_id, get_workspace_by_id


router = APIRouter(prefix="/{workspace_id}/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    new_task = Task(
        title=task.title,
        content=task.content,
        creator_id=member.user_id,
        owner_id=member.user_id,
        workspace_id=task.workspace_id,
        due_date=task.due_date,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get(
    "/", 
    response_model=PaginatedTaskResponse, 
    dependencies=[Depends(require_membership), Depends(get_workspace_by_id)]
)
def get_tasks(
    workspace_id: int, 
    db: DbSession, 
    skip  : Annotated[int, Query(ge=0)] = 0,
    limit : Annotated[int, Query(g=1, le=10)] = 10  
):
    count_result = db.execute(select(func.count()).select_from(Task)).scalar()
    total = count_result or 0
    
    tasks = (
        db.execute(select(Task)
        .where(Task.workspace_id == workspace_id)
        .order_by(Task.date_created.desc())
        .offset(skip).limit(limit))
        .scalars().all()
    )

    has_more = skip + len(tasks) < total
    response = PaginatedTaskResponse(
        tasks    = [TaskResponse.model_validate(t) for t in tasks],
        total    = total,
        skip     = skip,
        limit    = limit,
        has_more = has_more
    )

    return response


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


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_membership)],
)
def update_task_full(
    task_id: int,
    workspace_id: int,
    task_data: TaskCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = get_task_by_id(task_id, db)
    user = get_user_by_id(member.user_id, db)

    if user.id != task.owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authorized to update this task",
        )

    update = task_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task, attribute_names=["creator"])
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
    current_user: Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = get_task_by_id(task_id, db)

    if task.owner_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the owner of this task",
        )

    task.is_completed = True

    db.commit()
    db.refresh(task)

    return task


@router.patch(
    "/{task_id}/owner",
    response_model=TaskResponse,
    dependencies=[Depends(require_admin)],
)
def make_owner(
    user_id: int,
    task_id: int,
    workspace_id: int,
    db: DbSession,
):
    member = get_target_membership(workspace_id, user_id, db)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )

    task = get_task_by_id(task_id, db)
    task.owner_id = member.user_id

    db.commit()
    db.refresh(task)

    return task


@router.patch(
    "/{task_id}/move",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_admin)],
)
def move_task(
    task_id: int,
    workspace_id: int,
    task_data: TaskMove,
    db: DbSession,
):
    task = get_task_by_id(task_id, db)
    task.workspace_id = task_data.workspace_id

    db.commit()
    db.refresh(task)

    workspace = (
        db.execute(select(Workspace).where(Workspace.id == task.workspace_id))
        .scalars()
        .first()
    )

    return workspace

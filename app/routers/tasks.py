from fastapi import APIRouter, HTTPException, status, Depends

from typing import Annotated

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import CurrentUser

from app.utility import get_target_membership, require_membership, require_admin
from app.models import User, Task, Workspace, WorkspaceMember
from app.schemas import (
    TaskCreate, 
    TaskResponse, 
    TaskUpdate, 
    TaskMove,
    WorkspaceResponse
)


router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task         : TaskCreate, 
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[WorkspaceMember, Depends(require_membership)], 
):
    new_task = Task(
        title        = task.title,
        content      = task.content,
        creator_id   = current_user.user_id,
        owner_id     = current_user.user_id,
        workspace_id = task.workspace_id,
        due_date     = task.due_date,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/me/{task_id}/{workspace_id}", response_model=TaskResponse)
def get_task(
    task_id      : int, 
    workspace_id : int,
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[Session, Depends(require_membership)],
):
    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task


@router.patch("/make-owner/{workspace_id}/{user_id}/{task_id}", response_model=WorkspaceResponse)
def make_owner(
    user_id      : int,
    task_id      : int,
    workspace_id : int,
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[WorkspaceMember, Depends(require_admin)],
):
    member = get_target_membership(workspace_id, user_id, db)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of this workspace"
        )

    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Workspace not found")

    task.owner_id = member.user_id
    
    db.commit()
    db.refresh(task)
    
    return task


@router.patch("/{task_id}/{workspace_id}", response_model=TaskResponse)
def update_task_partial(
    task_id      : int, 
    workspace_id : int,
    task_data    : TaskUpdate, 
    db           : Annotated[Session, Depends(get_db)],
    user         : Annotated[WorkspaceMember, Depends(require_membership)],
):
    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update = task_data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task
    
    
@router.put("/{task_id}/{workspace_id}", response_model=TaskResponse)
def update_task_full(
    task_id      : int, 
    workspace_id : int,
    task_data    : TaskCreate, 
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[WorkspaceMember, Depends(require_membership)], 
):
    task_result = db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    user_result = db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if user.id != task.creator_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to update this task")

    task.title = task_data.title
    task.content = task_data.content
    task.creator_id = user.id
    task.workspace_id = task_data.workspace_id
    task.is_public = task_data.is_public
    task.due_date = task_data.due_date

    db.commit()
    db.refresh(task, attribute_names=['creator'])
    return task


@router.patch("/{task_id}/{workspace_id}", response_model=TaskResponse)
def complete_task(
    task_id      : int, 
    workspace_id : int, 
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[WorkspaceMember, Depends(require_membership)], 
) :
    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task :
        raise  HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    if task.owner_id == current_user.user_id :
        raise  HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not the owner of this task"
        )
        
    task.is_completed = True

    db.commit()
    db.refresh(task)

    return task


@router.patch("{task_id}/{workspace_id}/", response_model=WorkspaceResponse)
def move_task(
    task_id      : int,
    workspace_id : int,
    task_data    : TaskMove,
    db           : Annotated[Session, Depends(get_db)],
    user         : Annotated[WorkspaceMember, Depends(require_admin)],
):
    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.workspace_id = task_data.workspace_id

    db.commit()
    db.refresh(task)

    workspace = db.execute(
        select(Workspace)
        .where(Workspace.id == task.workspace_id)
    ).scalars().first()

    return workspace


@router.delete("/{task_id}/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id      : int,
    workspace_id : int,
    db           : Annotated[Session, Depends(get_db)],
    current_user : Annotated[WorkspaceMember, Depends(require_admin)],
):
    task = db.execute(
        select(Task).where(Task.id == task_id)
    ).scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    db.delete(task)
    db.commit()

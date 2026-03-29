from fastapi import APIRouter, HTTPException, status, Depends

from typing import Annotated

from sqlalchemy import select, func
from sqlalchemy.orm import Session


from database import get_db
from models import Task, User
from schemas import (
    TaskCreate, TaskResponse, TaskUpdate,
    UserCreate, UserPublic, UserPrivate, UserUpdate
)

router = APIRouter()

@router.post("/{user_id}", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(user_id: int, task: TaskCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_task = Task(
        title=task.title,
        content=task.content,
        creator_id=user_id,
        is_public=task.is_public,
        due_date=task.due_date,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task



@router.get("all/{user_id}", response_model=list[TaskResponse])
def get_all_tasks(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = db.execute(select(Task).where(Task.creator_id == user_id))
    tasks = result.scalars().all()

    return tasks


@app.get("/{task_id}/{user_id}", response_model=TaskResponse)
def get_task(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = db.execute(select(Task).where(Task.creator_id == user_id))
    tasks = result.scalars().first()

    return tasks


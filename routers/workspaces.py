from fastapi import APIRouter, Depends, status, HTTPException

from typing import Annotated

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import User, Task, Workspace
from schemas import (
WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
)

router = APIRouter()

@router.post("/{user_id}", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
        user_id: int,
        workspace: WorkspaceCreate,
        db: Annotated[Session, Depends(get_db)]
):
    user_result = db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_workspace = Workspace(
        title=workspace.title,
        description=workspace.description,
        due_date=workspace.due_date,
    )

    new_workspace.members.append(user)
    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    return new_workspace



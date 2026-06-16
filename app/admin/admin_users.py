from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func

from app.database import DbSession
from app.models import User
from app.schemas import SuperUserResponse, PaginatedSuperUserResponse
from app.dependencies import require_superuser
from app.utils import get_user_by_id


router = APIRouter()


@router.get(
    "/all", response_model=PaginatedSuperUserResponse, dependencies=[Depends(require_superuser)]
)
def get_all_users(
    db    : DbSession, 
    skip  : Annotated[int, Query(ge=0)] = 0,
    limit : Annotated[int, Query(ge=1, le=100)] = 100
):
    result_count = db.execute(select(func.count()).select_from(User)).scalar()
    total = result_count or 0
    
    users = (
        db.execute(select(User)
        .order_by(User.joined_at.desc())
        .offset(skip).limit(limit))
        .scalars().all()
    )

    has_more = skip + len(users) < total

    response = PaginatedSuperUserResponse(
        users    = [SuperUserResponse.model_validate(u) for u in users],
        total    = total,
        skip     = skip,
        limit    = limit,
        has_more = has_more,
    )
    return response


@router.get(
    "/{user_id}", response_model=SuperUserResponse, dependencies=[Depends(require_superuser)]
)
def get_user(user_id: int, db: DbSession):
    user = get_user_by_id(user_id, db)
    return user

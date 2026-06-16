from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException

from app.auth import CurrentUser
from app.admin import admin_users
from app.database import DbSession
from app.models import Task, User, Workspace, WorkspaceMember
from app.routers import tasks, users, workspaces

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="templates"), name="static")
app.mount("/media", StaticFiles(directory="templates"), name="static")

app.include_router(users.router, prefix="/api/users", tags=["user"])
app.include_router(tasks.router, prefix="/api/workspaces", tags=["task"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])
app.include_router(admin_users.router, prefix="/api/admin-users", tags=["admin_users"])


@app.get("", include_in_schema=False)
def home(request: Request, current_user: CurrentUser, db: DbSession):
    pending_workspaces = (
        db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .join(Task, Task.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == current_user.id,
                Task.is_completed == False
            )
            .distinct()  # prevent duplicate workspaces if multiple incomplete tasks
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="pending.html",
        context={"pending_workspaces": pending_workspaces, "title": "Home"},
    )


# ======================================================================================================================
# EXCEPTION HANDLER
# ======================================================================================================================


@app.exception_handler(HTTPException)
def general_exception_handler(request: Request, exc: HTTPException):

    message = exc.detail if exc.detail else "An error occurred, please try again"

    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exc.status_code, content={"message": message})

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": exc.status_code,
            "message": message,
            "title": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"message": exc.errors()},
        )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request, please check your input and try again",
        },
    )

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin import admin_users
from app.routers import folders, tasks, users, workspaces, resources, conversations
from app.database import DbSession
from app.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent / "static"),
    name="static",
)

app.include_router(users.router, prefix="/api/users")
app.include_router(workspaces.router, prefix="/api/workspaces")
app.include_router(conversations.router, prefix="/api/workspaces")
app.include_router(tasks.router, prefix="/api/workspaces")
app.include_router(resources.router, prefix="/api/workspaces")
app.include_router(folders.router, prefix="/api/folders")
app.include_router(admin_users.router, prefix="/api/admin-users")


# ======================================================================================================================
# EXCEPTION HANDLER
# ======================================================================================================================

@app.get("/health")
def health_check(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE, detail = "Database Unavailable"
        ) from exc

    return {"status" : "healthy"}

@app.exception_handler(StarletteHTTPException)
def general_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if exc.detail else "An error occurred, please try again"
    return JSONResponse(status_code=exc.status_code, content={"message": message})


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors()},
    )

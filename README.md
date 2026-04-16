# WorkspaceApp

A full-stack collaborative task management web application built with **FastAPI**, **PostgreSQL**, and **React**.

Users can create and manage workspaces individually or with invited members. Each workspace tracks tasks with deadlines and displays an aggregate completion rate calculated from the ratio of completed to total tasks.

## Features

- **Workspaces** — create shared project spaces, invite members, and track overall progress via a completion rate
- **Dual-ownership tasks** — tasks have both a *creator* (who made it) and an *owner* (who it's assigned to), which can be different users
- **Role-based access** — workspace admins can add and remove members; standard members can create and modify tasks freely
- **Scoped visibility** — workspace content (tasks, members) is only visible to workspace members
- **User accounts** — register, login, update profile, change password, delete account
- **JWT authentication** — stateless auth via Bearer tokens with Argon2 password hashing
- **Full CRUD** — complete create, read, update, and delete operations across all entities: users, workspaces, members, and tasks

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Backend | FastAPI |
| Data validation | Pydantic |
| Middleware / requests | Starlette |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | PostgreSQL |
| Auth | PyJWT + pwdlib (Argon2) |

## Data Model

The schema involves multiple levels of relational complexity:

- **User ↔ Workspace** — many-to-many membership via a `WorkspaceMember` association table, which also stores the member's role (`admin` or `member`)
- **Task** — belongs to a workspace, and carries two separate user foreign keys: `creator_id` and `owner_id`
- **Workspace** — aggregates task completion rate from the ratio of completed to total tasks across all its tasks

## Project Structure

```
WorkspaceApp/
├── app/
│   ├── main.py          # App entry point, router registration, exception handlers
│   ├── auth.py          # JWT creation/verification, password hashing, CurrentUser dependency
│   ├── config.py        # Settings (secret key, token expiry, etc.)
│   ├── database.py      # SQLAlchemy engine and session
│   ├── models/          # ORM models: User, Task, Workspace, WorkspaceMember
│   ├── routers/         # Route handlers: users, tasks, workspaces
│   ├── schemas/         # Pydantic request/response schemas
│   └── admin/           # Admin-only user management routes
├── alembic/             # Database migration scripts
└── pyproject.toml
```

## Getting Started

### Install dependencies

```bash
pip install uv
uv sync
```

### Configure environment

Create a `.env` file with at minimum:

```
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost/workspaceapp
```

### Run migrations

```bash
alembic upgrade head
```

### Start the backend

```bash
fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`. Interactive docs are at `/docs`.

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/user` | Register a new user |
| `POST` | `/api/user/login` | Login and receive a JWT |
| `GET` | `/api/user/me` | Get current user profile |
| `PATCH` | `/api/user/me` | Update profile |
| `DELETE` | `/api/user/me` | Delete account |
| `POST` | `/api/workspaces` | Create a workspace |
| `GET` | `/api/workspaces/{id}` | Get workspace details and completion rate |
| `PATCH` | `/api/workspaces/members/add/{ws_id}/{user_id}` | Add a member (admin only) |
| `PATCH` | `/api/workspaces/members/remove/{ws_id}/{user_id}` | Remove a member (admin only) |
| `PATCH` | `/api/workspaces/members/make-admin/{ws_id}/{user_id}` | Promote a member to admin |
| `POST` | `/api/task` | Create a task |
| `PATCH` | `/api/task/{id}` | Update a task |
| `DELETE` | `/api/task/{id}` | Delete a task |

This project is currently under active development. The backend API is functional; the React frontend is in progress.

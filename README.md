# WorkspaceApp

A full-stack collaborative task management app built with **FastAPI**, **PostgreSQL**, and **React**.

Users create workspaces, invite members, and track tasks with deadlines, completion rates, pinning, and archiving. The frontend is in active development — a persistent sidebar, top navbar, and kanban-style card layout are underway.

## Features

- **Workspaces** — shared project spaces with member invites, task tracking, and aggregate completion rate. Workspaces can be pinned or archived.
- **Dual-ownership tasks** — tasks have a _creator_ and an _owner_ (assignee), which can be different users; admins can reassign ownership.
- **Role-based access** — workspace admins manage members; members create and modify tasks freely.
- **Scoped visibility** — workspace content is visible only to members.
- **User accounts** — register, login, update profile, upload profile picture, change or reset password, delete account.
- **Profile pictures** — images are cropped (300×300), JPEG-optimized, and stored in S3-compatible object storage.
- **Password reset** — token-based flow with email delivery, SHA-256 hashed tokens, configurable expiration.
- **JWT auth** — stateless Bearer tokens with Argon2 password hashing.
- **Superuser system** — privileged accounts with a protected admin API for inspecting any user.
- **Pagination** — task list endpoints support `skip`/`limit` with `has_more` indicators.
- **Comprehensive tests** — 170+ tests covering all endpoints, auth, S3 uploads, and password reset flows with mocked external services.

## Tech Stack

| Layer            | Technology                            |
| ---------------- | ------------------------------------- |
| Frontend         | React 19 + Vite                       |
| Backend          | FastAPI + SQLAlchemy 2.0 + Alembic    |
| Database         | PostgreSQL                            |
| Auth             | PyJWT + pwdlib (Argon2)               |
| Object storage   | AWS S3 (boto3)                        |
| Image processing | Pillow                                |
| Email            | smtplib + Jinja2 templates            |
| Testing          | pytest, TestClient, moto (S3 mocking) |

## Project Structure

```
WorkspaceApp/
├── backend/
│   ├── app/
│   │   ├── main.py              # App entry point, CORS, exception handlers
│   │   ├── auth.py              # JWT, password hashing, reset tokens, CurrentUser
│   │   ├── config.py            # Environment settings
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── dependencies.py      # Shared deps (require_admin, require_membership)
│   │   ├── models/              # ORM models: User, Task, Workspace, WorkspaceMember, PasswordResetToken
│   │   ├── routers/             # users, tasks, workspaces
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── utils/               # image_utils, email_utils, queries
│   │   ├── admin/               # Superuser-only endpoints
│   │   └── scripts/             # check_s3, make_admin, seed
│   ├── alembic/                 # Database migrations
│   ├── templates/               # Email templates
│   ├── tests/                   # 170+ tests
│   ├── static/
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── styles/
│   │   └── utils/
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── pyproject.toml
```

## Getting Started

### Prerequisites

- Python 3.14+, PostgreSQL, Node.js
- S3-compatible object store (optional — tests use mocked S3)

### Backend setup

```bash
cd backend
pip install uv
uv sync
```

Create a `.env` in `backend/`:

```ini
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+psycopg://user:password@localhost/workspaceapp

# S3 (optional — profile pic uploads will fail without these)
S3_BUCKET_NAME=your-bucket
S3_REGION=us-east-2
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key

# Email (optional — password reset emails will fail without these)
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email
MAIL_PASSWORD=your-password
MAIL_FROM=noreply@example.com
FRONTEND_URL=http://localhost:5173
```

```bash
alembic upgrade head
fastapi dev app/main.py
```

API at `http://localhost:8000`, interactive docs at `/docs`.

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

App at `http://localhost:5173`. The backend allows CORS from this origin.

## API Overview

### Users

| Method   | Endpoint                     | Auth   | Description                        |
| -------- | ---------------------------- | ------ | ---------------------------------- |
| `POST`   | `/api/users`                 | —      | Register                           |
| `POST`   | `/api/users/login`           | —      | Login (returns JWT)                |
| `GET`    | `/api/users/me`              | Bearer | Current user profile               |
| `PATCH`  | `/api/users/me`              | Bearer | Update profile                     |
| `DELETE` | `/api/users/me`              | Bearer | Delete account                     |
| `GET`    | `/api/users/{user_id}`       | —      | Public profile                     |
| `GET`    | `/api/users/me/workspaces`   | Bearer | List current user's workspaces     |
| `PATCH`  | `/api/users/me/password`     | Bearer | Change password                    |
| `PATCH`  | `/api/users/me/picture`      | Bearer | Upload profile picture (multipart) |
| `DELETE` | `/api/users/me/picture`      | Bearer | Delete profile picture             |
| `POST`   | `/api/users/forgot-password` | —      | Request password reset email       |
| `POST`   | `/api/users/reset-password`  | —      | Reset password with token          |

### Workspaces

| Method   | Endpoint                                       | Auth   | Description              |
| -------- | ---------------------------------------------- | ------ | ------------------------ |
| `POST`   | `/api/workspaces`                              | Bearer | Create                   |
| `GET`    | `/api/workspaces/{id}`                         | —      | Details (public)         |
| `PATCH`  | `/api/workspaces/{id}`                         | Bearer | Partial update (member)  |
| `DELETE` | `/api/workspaces/{id}`                         | Bearer | Delete (admin)           |
| `GET`    | `/api/workspaces/{id}/members`                 | Bearer | List members (member)    |
| `PATCH`  | `/api/workspaces/{id}/members/{user_id}`       | Bearer | Add member (admin)       |
| `PATCH`  | `/api/workspaces/{id}/members/{user_id}/admin` | Bearer | Promote to admin (admin) |
| `DELETE` | `/api/workspaces/{id}/members/me`              | Bearer | Leave workspace          |
| `DELETE` | `/api/workspaces/{id}/members/{user_id}`       | Bearer | Remove member (admin)    |

### Tasks

| Method   | Endpoint                                           | Auth   | Description                          |
| -------- | -------------------------------------------------- | ------ | ------------------------------------ |
| `POST`   | `/api/workspaces/{ws_id}/tasks`                    | Bearer | Create (member)                      |
| `GET`    | `/api/workspaces/{ws_id}/tasks`                    | Bearer | List (paginated: `?skip=0&limit=10`) |
| `GET`    | `/api/workspaces/{ws_id}/tasks/{task_id}`          | Bearer | Get                                  |
| `PATCH`  | `/api/workspaces/{ws_id}/tasks/{task_id}`          | Bearer | Partial update                       |
| `DELETE` | `/api/workspaces/{ws_id}/tasks/{task_id}`          | Bearer | Delete (admin)                       |
| `PATCH`  | `/api/workspaces/{ws_id}/tasks/{task_id}/complete` | Bearer | Mark complete                        |
| `PATCH`  | `/api/workspaces/{ws_id}/tasks/{task_id}/owner`    | Bearer | Change owner (admin)                 |
| `PATCH`  | `/api/workspaces/{ws_id}/tasks/{task_id}/move`     | Bearer | Move to another workspace (admin)    |

### Admin (superuser only)

| Method | Endpoint                     | Description        |
| ------ | ---------------------------- | ------------------ |
| `GET`  | `/api/admin-users/all`       | List all users     |
| `GET`  | `/api/admin-users/{user_id}` | Get any user by ID |

## Testing

```bash
cd backend
pytest tests/
```

- **Database**: Each session creates a fresh schema; each test runs in a rolled-back transaction.
- **S3**: `moto` provides an in-memory mock S3 bucket — no real AWS calls.
- **Email**: SMTP is patched with `unittest.mock` — no real connections.

## Development Status

The backend is feature-complete. The React frontend is in active development — UI includes a persistent sidebar (workspace history, pinned items), a top navbar with search, and a kanban-style card grid sorted by urgency and due date.

"""
Seed the WorkspaceApp database with realistic test data.

Usage (from the backend/ directory):
    uv run --project .. python populate_db.py

Requires the backend .env to be present and the database to be migrated.

Optional: place profile-picture PNGs in a 'populate_images/' folder next to
this file.  Filenames must match the 'image' keys in USERS below.
If an image file is missing, the user simply gets the default avatar.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from starlette.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import PasswordResetToken, RefreshToken, Task, User, Workspace, WorkspaceMember
from app.utils.image_utils import _get_s3_client

POPULATE_IMAGES_DIR = Path("populate_images")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

USERS = [
    {
        "username": "mikelange",
        "email": "mikelange@workspaceapp.dev",
        "password": "Password1!",
        "image": "mikelange.jpg",
    },
    {
        "username": "alicecode",
        "email": "alice@workspaceapp.dev",
        "password": "Password2!",
        "image": "alice.jpg",
    },
    {
        "username": "bobjones",
        "email": "bob@workspaceapp.dev",
        "password": "Password3!",
        "image": "bob.png",
    },
    {
        "username": "carolpm",
        "email": "carol@workspaceapp.dev",
        "password": "Password4!",
        "image": "carol.png",
    },
    {
        "username": "davetester",
        "email": "dave@workspaceapp.dev",
        "password": "Password5!",
        # no image — uses default avatar
    },
]

# due_date_days: positive = days from now, negative = days ago, None = no deadline
WORKSPACES = [
    {
        "title": "Portfolio Website",
        "description": "Personal portfolio site showcasing projects and skills. Needs a redesign before the job application deadline.",
        "creator": "mikelange",
        "due_date_days": -5,        # overdue → error dot
        "is_pinned": True,
        "members": [
            {"username": "alicecode", "make_admin": False},
            {"username": "bobjones",  "make_admin": False},
        ],
        "tasks": [
            {
                "title": "Write about section",
                "content": "Draft a compelling 'About Me' section that summarises background, skills, and what kind of roles you're targeting.",
                "created_by": "mikelange",
                "due_date_days": -10,
                "completed": True,
            },
            {
                "title": "Design project cards",
                "content": "Create card components for each featured project. Include screenshot, tech stack tags, live link, and GitHub link.",
                "created_by": "bobjones",
                "due_date_days": -7,
                "completed": True,
            },
            {
                "title": "Add contact form",
                "content": "Implement a contact form that emails submissions to the owner. Validate inputs on the frontend and add honeypot for spam prevention.",
                "created_by": "alicecode",
                "due_date_days": -2,
                "completed": False,
            },
            {
                "title": "Optimise for mobile",
                "content": "Audit every page on 375px, 390px, and 428px viewports. Fix any layout overflow, illegible text, or broken images.",
                "created_by": "mikelange",
                "due_date_days": None,
                "completed": False,
            },
        ],
    },
    {
        "title": "Mobile App MVP",
        "description": "First shippable version of the companion mobile app. Focus on core auth, workspace listing, and task creation flows.",
        "creator": "mikelange",
        "due_date_days": 2,         # due very soon → warning dot
        "is_pinned": False,
        "members": [
            {"username": "alicecode",  "make_admin": True},
            {"username": "carolpm",    "make_admin": False},
            {"username": "davetester", "make_admin": False},
        ],
        "tasks": [
            {
                "title": "Set up React Native project",
                "content": "Initialise the project with Expo, configure ESLint/Prettier, and push the skeleton to GitHub.",
                "created_by": "alicecode",
                "due_date_days": -8,
                "completed": True,
            },
            {
                "title": "Build auth screens",
                "content": "Implement login and registration screens. Wire up token storage with SecureStore and handle refresh logic.",
                "created_by": "alicecode",
                "due_date_days": -4,
                "completed": True,
            },
            {
                "title": "Workspace list screen",
                "content": "Fetch and display the current user's workspaces. Support pull-to-refresh and an empty state illustration.",
                "created_by": "mikelange",
                "due_date_days": -1,
                "completed": True,
            },
            {
                "title": "Task creation flow",
                "content": "Bottom-sheet form to create a task inside a workspace. Validate fields and show inline errors.",
                "created_by": "carolpm",
                "due_date_days": 1,
                "completed": False,
            },
            {
                "title": "Write smoke tests",
                "content": "Cover the happy path for login, workspace load, and task creation using Jest and React Native Testing Library.",
                "created_by": "davetester",
                "due_date_days": 2,
                "completed": False,
            },
            {
                "title": "Submit to TestFlight",
                "content": "Configure EAS build, bump version to 0.1.0, and submit an internal build to TestFlight for QA review.",
                "created_by": "alicecode",
                "due_date_days": 2,
                "completed": False,
            },
        ],
    },
    {
        "title": "Internal Dashboard",
        "description": "Analytics dashboard for internal team metrics. No hard deadline — we ship when it is useful, not on a schedule.",
        "creator": "alicecode",
        "due_date_days": None,      # no deadline, tasks exist → success dot
        "is_pinned": False,
        "members": [
            {"username": "mikelange", "make_admin": False},
            {"username": "carolpm",   "make_admin": False},
        ],
        "tasks": [
            {
                "title": "Design data model",
                "content": "Map out which metrics are worth tracking. Define the schema for events, aggregates, and time-series tables.",
                "created_by": "alicecode",
                "due_date_days": None,
                "completed": False,
            },
            {
                "title": "Build chart components",
                "content": "Create reusable LineChart, BarChart, and KPICard components using Recharts. Make them responsive and theme-aware.",
                "created_by": "mikelange",
                "due_date_days": None,
                "completed": False,
            },
            {
                "title": "Connect to live data",
                "content": "Wire up the charts to the real API. Handle loading, error, and empty states for each panel.",
                "created_by": "carolpm",
                "due_date_days": None,
                "completed": False,
            },
        ],
    },
    {
        "title": "Q2 Marketing Campaign",
        "description": "Second quarter campaign across email, social, and paid channels. All deliverables wrapped up.",
        "creator": "carolpm",
        "due_date_days": -10,       # past deadline but all tasks complete → success dot
        "is_pinned": False,
        "members": [
            {"username": "mikelange", "make_admin": False},
            {"username": "bobjones",  "make_admin": False},
        ],
        "tasks": [
            {
                "title": "Write email sequence",
                "content": "Draft a five-email nurture sequence. Subject lines, body copy, and CTAs reviewed and approved by the team.",
                "created_by": "carolpm",
                "due_date_days": -20,
                "completed": True,
            },
            {
                "title": "Design social assets",
                "content": "Create a set of 10 social posts (1:1, 4:5, 16:9) in brand colours. Export as PNG and upload to the shared drive.",
                "created_by": "bobjones",
                "due_date_days": -18,
                "completed": True,
            },
            {
                "title": "Set up ad campaigns",
                "content": "Configure Google Ads and Meta campaigns with the agreed budgets. Set up UTM tracking on all landing page links.",
                "created_by": "carolpm",
                "due_date_days": -15,
                "completed": True,
            },
            {
                "title": "Write post-campaign report",
                "content": "Summarise results: impressions, clicks, conversions, CPL. Compare against Q1 benchmarks and propose Q3 adjustments.",
                "created_by": "mikelange",
                "due_date_days": -12,
                "completed": True,
            },
        ],
    },
    {
        "title": "Infrastructure Upgrade",
        "description": "Migrate the production stack to the new cloud provider. No tasks added yet — planning phase.",
        "creator": "davetester",
        "due_date_days": 14,        # future, no tasks → neutral dot
        "is_pinned": False,
        "members": [],
        "tasks": [],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def clear_existing_data() -> None:
    # Delete S3 profile pictures first (need DB records to know which files)
    with SessionLocal() as db:
        filenames = db.execute(
            select(User.image_file).where(User.image_file.is_not(None))
        ).scalars().all()

    if filenames:
        s3 = _get_s3_client()
        s3.delete_objects(
            Bucket=settings.s3_bucket_name,
            Delete={"Objects": [{"Key": f"profile_pics/{f}"} for f in filenames]},
        )
        print(f"  Deleted {len(filenames)} profile picture(s) from S3")

    # Clear tables in FK-safe order
    with SessionLocal() as db:
        db.execute(delete(RefreshToken))
        db.execute(delete(PasswordResetToken))
        db.execute(delete(Task))
        db.execute(delete(WorkspaceMember))
        db.execute(delete(Workspace))
        db.execute(delete(User))
        db.commit()

    print("  Cleared existing database records")


# ---------------------------------------------------------------------------
# Main populate function
# ---------------------------------------------------------------------------

def populate() -> None:
    with TestClient(app) as client:
        print("\nClearing existing data...")
        clear_existing_data()

        # ---- Users --------------------------------------------------------
        user_map: dict[str, dict] = {}   # username → {id, token}

        print(f"\nCreating {len(USERS)} users...")
        for user_data in USERS:
            res = client.post(
                "/api/users",
                json={
                    "username": user_data["username"],
                    "email":    user_data["email"],
                    "password": user_data["password"],
                },
            )
            res.raise_for_status()
            user = res.json()
            print(f"  Created: {user['username']}")

            # Log in to get tokens
            res = client.post(
                "/api/users/login",
                data={
                    "username": user_data["email"],
                    "password": user_data["password"],
                },
            )
            res.raise_for_status()
            token = res.json()["access_token"]

            # Optional profile picture
            if image_name := user_data.get("image"):
                image_path = POPULATE_IMAGES_DIR / image_name
                if image_path.exists():
                    res = client.patch(
                        "/api/users/me/picture",
                        files={"file": (image_name, image_path.read_bytes(), "image/png")},
                        headers=_auth_header(token),
                    )
                    res.raise_for_status()
                    print(f"    Uploaded profile picture: {image_name}")

            user_map[user_data["username"]] = {"id": user["id"], "token": token}

        # ---- Workspaces ---------------------------------------------------
        now = datetime.now(UTC)

        print(f"\nCreating {len(WORKSPACES)} workspaces...")
        for ws_data in WORKSPACES:
            creator = user_map[ws_data["creator"]]

            due_date = None
            if ws_data["due_date_days"] is not None:
                due_date = (now + timedelta(days=ws_data["due_date_days"])).isoformat()

            res = client.post(
                "/api/workspaces",
                json={
                    "title":       ws_data["title"],
                    "description": ws_data["description"],
                    "due_date":    due_date,
                },
                headers=_auth_header(creator["token"]),
            )
            res.raise_for_status()
            ws = res.json()
            ws_id = ws["id"]
            print(f"  Created: '{ws['title']}' (id={ws_id})")

            # Pin if requested
            if ws_data.get("is_pinned"):
                res = client.patch(
                    f"/api/workspaces/{ws_id}",
                    json={"is_pinned": True},
                    headers=_auth_header(creator["token"]),
                )
                res.raise_for_status()
                print(f"    Pinned")

            # Add members
            for member_data in ws_data["members"]:
                member = user_map[member_data["username"]]

                res = client.patch(
                    f"/api/workspaces/{ws_id}/members/{member['id']}",
                    headers=_auth_header(creator["token"]),
                )
                res.raise_for_status()

                if member_data.get("make_admin"):
                    res = client.patch(
                        f"/api/workspaces/{ws_id}/members/{member['id']}/admin",
                        headers=_auth_header(creator["token"]),
                    )
                    res.raise_for_status()
                    print(f"    Added member: {member_data['username']} (admin)")
                else:
                    print(f"    Added member: {member_data['username']}")

            # Create tasks
            for task_data in ws_data["tasks"]:
                task_creator = user_map[task_data["created_by"]]

                task_due = None
                if task_data["due_date_days"] is not None:
                    task_due = (now + timedelta(days=task_data["due_date_days"])).isoformat()

                res = client.post(
                    f"/api/workspaces/{ws_id}/tasks/",
                    json={
                        "title":        task_data["title"],
                        "content":      task_data["content"],
                        "creator_id":   task_creator["id"],
                        "owner_id":     task_creator["id"],
                        "workspace_id": ws_id,
                        "due_date":     task_due,
                    },
                    headers=_auth_header(task_creator["token"]),
                )
                res.raise_for_status()
                task = res.json()
                task_id = task["id"]

                if task_data["completed"]:
                    res = client.patch(
                        f"/api/workspaces/{ws_id}/tasks/{task_id}/complete",
                        headers=_auth_header(task_creator["token"]),
                    )
                    res.raise_for_status()
                    print(f"    Task (done): '{task_data['title']}'")
                else:
                    print(f"    Task (open): '{task_data['title']}'")

    # Summary
    total_tasks = sum(len(ws["tasks"]) for ws in WORKSPACES)
    completed_tasks = sum(
        sum(1 for t in ws["tasks"] if t["completed"]) for ws in WORKSPACES
    )

    print("\nDone!")
    print(f"  {len(USERS)} users")
    print(f"  {len(WORKSPACES)} workspaces")
    print(f"  {total_tasks} tasks ({completed_tasks} completed, {total_tasks - completed_tasks} open)")


if __name__ == "__main__":
    populate()

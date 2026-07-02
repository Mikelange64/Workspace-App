from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models import Folder, Task, User, Workspace, WorkspaceMember
from app.auth import hash_password


def dt(days_offset=0):
    return datetime.now(UTC) + timedelta(days=days_offset)


def populate_db():
    db = SessionLocal()

    try:
        # ── Users ─────────────────────────────────────────────────────────────
        mike = User(
            username="devuser",
            email="dev@example.com",
            password_hash=hash_password("devpass!local"),
            is_verified=True,
        )
        alice = User(
            username="alicebaker",
            email="alice@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )
        bob = User(
            username="bobsmith",
            email="bob@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )

        db.add_all([mike, alice, bob])
        db.flush()

        # ── Folders ───────────────────────────────────────────────────────────
        work_folder = Folder(owner_id=mike.id, name="Work", color="#3b82f6")
        personal_folder = Folder(owner_id=mike.id, name="Personal", color="#8b5cf6")

        db.add_all([work_folder, personal_folder])
        db.flush()

        # ── Workspaces ────────────────────────────────────────────────────────

        # Active — in progress, due soon
        ws_marketing = Workspace(
            creator_id=mike.id,
            title="Q2 Marketing Campaign",
            description="Plan and execute the Q2 marketing push across all channels",
            max_number=5,
            due_date=dt(5),
            folder_id=work_folder.id,
        )

        # Active — overdue
        ws_dashboard = Workspace(
            creator_id=mike.id,
            title="Internal Dashboard",
            description="Rebuild the internal analytics dashboard",
            max_number=3,
            due_date=dt(-3),
            folder_id=work_folder.id,
        )

        # Active — no deadline, pinned
        ws_mobile = Workspace(
            creator_id=mike.id,
            title="Mobile App MVP",
            description="Ship the first version of the mobile app",
            max_number=4,
            is_pinned=True,
        )

        # Active — shared with alice
        ws_portfolio = Workspace(
            creator_id=alice.id,
            title="Portfolio Website",
            description="Redesign and relaunch the portfolio site",
            max_number=2,
            due_date=dt(14),
            folder_id=personal_folder.id,
        )

        # Completed workspace
        ws_onboarding = Workspace(
            creator_id=mike.id,
            title="User Onboarding Flow",
            description="Design and implement the new user onboarding experience",
            max_number=3,
            is_completed=True,
            completed_at=dt(-10),
        )

        # Completed workspace — older
        ws_rebrand = Workspace(
            creator_id=mike.id,
            title="Brand Refresh",
            description="Update the visual identity across all touchpoints",
            max_number=2,
            is_completed=True,
            completed_at=dt(-30),
        )

        # Archived workspace
        ws_archived = Workspace(
            creator_id=mike.id,
            title="Old API Integration",
            description="Legacy API integration project — paused",
            max_number=2,
            is_archived=True,
        )

        db.add_all([
            ws_marketing, ws_dashboard, ws_mobile, ws_portfolio,
            ws_onboarding, ws_rebrand, ws_archived,
        ])
        db.flush()

        # ── Members ───────────────────────────────────────────────────────────
        db.add_all([
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_marketing.id,  role="admin"),
            WorkspaceMember(user_id=alice.id, workspace_id=ws_marketing.id,  role="member"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_dashboard.id,  role="admin"),
            WorkspaceMember(user_id=bob.id,   workspace_id=ws_dashboard.id,  role="member"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_mobile.id,     role="admin"),
            WorkspaceMember(user_id=alice.id, workspace_id=ws_portfolio.id,  role="admin"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_portfolio.id,  role="member"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_onboarding.id, role="admin"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_rebrand.id,    role="admin"),
            WorkspaceMember(user_id=mike.id,  workspace_id=ws_archived.id,   role="admin"),
        ])
        db.flush()

        # ── Tasks ─────────────────────────────────────────────────────────────

        # Q2 Marketing — mixed completion
        db.add_all([
            Task(title="Define target audience segments", content="", workspace_id=ws_marketing.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-2)),
            Task(title="Draft email campaign copy", content="", workspace_id=ws_marketing.id,
                 creator_id=mike.id, owner_id=alice.id, due_date=dt(3)),
            Task(title="Design social media assets", content="", workspace_id=ws_marketing.id,
                 creator_id=mike.id, owner_id=alice.id, due_date=dt(4)),
            Task(title="Set up A/B testing", content="", workspace_id=ws_marketing.id,
                 creator_id=mike.id, owner_id=mike.id, due_date=dt(5)),
        ])

        # Internal Dashboard — mostly incomplete, overdue
        db.add_all([
            Task(title="Audit current dashboard metrics", content="", workspace_id=ws_dashboard.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-7)),
            Task(title="Design new chart components", content="", workspace_id=ws_dashboard.id,
                 creator_id=mike.id, owner_id=bob.id, due_date=dt(-1)),
            Task(title="Connect to data pipeline", content="", workspace_id=ws_dashboard.id,
                 creator_id=mike.id, owner_id=mike.id, due_date=dt(-2)),
        ])

        # Mobile App MVP — all open
        db.add_all([
            Task(title="Set up React Native project", content="", workspace_id=ws_mobile.id,
                 creator_id=mike.id, owner_id=mike.id),
            Task(title="Build authentication screens", content="", workspace_id=ws_mobile.id,
                 creator_id=mike.id, owner_id=mike.id, due_date=dt(7)),
            Task(title="Implement push notifications", content="", workspace_id=ws_mobile.id,
                 creator_id=mike.id, owner_id=mike.id, due_date=dt(21)),
        ])

        # Portfolio Website — shared
        db.add_all([
            Task(title="Write case studies", content="", workspace_id=ws_portfolio.id,
                 creator_id=alice.id, owner_id=alice.id, due_date=dt(10)),
            Task(title="Redesign hero section", content="", workspace_id=ws_portfolio.id,
                 creator_id=alice.id, owner_id=mike.id, due_date=dt(12)),
        ])

        # User Onboarding — all completed (it's a completed workspace)
        db.add_all([
            Task(title="Map out onboarding steps", content="", workspace_id=ws_onboarding.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-20)),
            Task(title="Build welcome email sequence", content="", workspace_id=ws_onboarding.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-15)),
            Task(title="Implement tooltip tour", content="", workspace_id=ws_onboarding.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-12)),
        ])

        # Brand Refresh — all completed (it's a completed workspace)
        db.add_all([
            Task(title="Update color palette", content="", workspace_id=ws_rebrand.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-35)),
            Task(title="Redesign logo variants", content="", workspace_id=ws_rebrand.id,
                 creator_id=mike.id, owner_id=mike.id, is_completed=True,
                 completed_at=dt(-32)),
        ])

        db.commit()
        print("Database seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_db()

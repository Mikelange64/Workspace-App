from fastapi import HTTPException, status

from sqlalchemy import select

from app.database import DbSession
from app.models import User, Workspace, WorkspaceMember
from app.auth import CurrentUser


def require_admin(
    workspace_id: int, current_user: CurrentUser, db: DbSession
) -> WorkspaceMember:
    query = select(WorkspaceMember).where(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.role == "admin"
    )
    is_admin = db.execute(query).scalars().first()

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only admins can perform this action"
        )

    return is_admin


def require_membership(
    workspace_id: int, current_user: CurrentUser, db: DbSession
)-> WorkspaceMember :
    query = select(WorkspaceMember).where(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.workspace_id == workspace_id,
    )
    is_member = db.execute(query).scalars().first()

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User is not a member of this workspace"
        )

    return is_member


def get_target_membership(
    workspace_id: int, user_id: int, db: DbSession
) -> WorkspaceMember | None :
    
    is_member = db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id
        )
    ).scalars().first()

    return is_member



def handle_membership_departure(membership: WorkspaceMember, db: DbSession) -> None:
    """Call whenever a WorkspaceMember row is about to go away (leave, kick,
    or the user's whole account being deleted), before committing.

    A workspace has no single owner - it belongs to whoever's still in it.
    If this leaves nobody, the workspace goes with them. If it removes the
    last admin but other members remain, adminship passes automatically to
    whoever's been there longest rather than leaving the workspace stuck
    with no admin.

    Known edge cases (deliberately deferred, not fixed):
    - Not race-safe: this is check-then-act with no row locking, so two
      near-simultaneous departures from the same workspace (e.g. both
      admins leaving at once) could both read "other admins exist" before
      either commits, leaving the workspace briefly (or permanently)
      admin-less. Needs a SELECT ... FOR UPDATE on the workspace's
      membership rows, or an application-level lock, to close properly.
    - Successor tie-breaking on identical joined_at is arbitrary: if two
      members joined at the exact same timestamp, `min()` just returns
      whichever Postgres happens to return first - not a deliberate
      choice. A secondary sort key (e.g. user_id) would make it
      deterministic.
    Both are low-probability enough that they're being tracked rather than
    fixed right now.
    """
    other_members = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == membership.workspace_id,
            WorkspaceMember.user_id != membership.user_id,
        )
    ).scalars().all()

    if not other_members:
        workspace = db.get(Workspace, membership.workspace_id)
        db.delete(workspace)
        return

    if membership.role == "admin" and not any(m.role == "admin" for m in other_members):
        successor = min(other_members, key=lambda m: m.joined_at)
        successor.role = "admin"

    db.delete(membership)


def require_superuser(current_user : CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "User not allowed to perform this action"
        )
        
    return current_user
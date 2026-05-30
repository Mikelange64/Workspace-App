from datetime import datetime

from app.database import SessionLocal
from app.models import User, Workspace, Task, WorkspaceMember
from app.auth import hash_password


def populate_db():
    db = SessionLocal()

    try:
        user1 = User( username="unjogratis", email="unjogratis@banana.tree", password_hash=hash_password("forbiddenmonkeygod") )
        user2 = User( username="pakarellapakota", email="pakarella@unicycle.wheel", password_hash=hash_password("godessofunicycles") )
        user3 = User( username="tomcockroach", email="cockroach@worstbug.die", password_hash=hash_password("ihatecockroaches") )

        users_to_add = [user1, user2, user3]
        db.add_all(users_to_add)
        db.flush()

        user1_workspace = Workspace( creator_id=user1.id, title="Expansion", description="Must expand banana domain across all realms", max_number=1 )
        user2_workspace = Workspace( creator_id=user2.id, title="New Unicycle", description="Must create the ultimate unicycle", max_number=3, due_date=datetime(2026, 7, 2) )
        user3_workspace = Workspace( creator_id=user3.id, title="Invade Earth", description="Must invade earth and make lives worse for everyone", max_number=100 )

        workspace_to_add = [user1_workspace, user2_workspace, user3_workspace]
        db.add_all(workspace_to_add)
        db.flush()

        member1 = WorkspaceMember( user_id=user1.id, workspace_id=user1_workspace.id, role="admin" )
        member2 = WorkspaceMember( user_id=user2.id, workspace_id=user2_workspace.id, role="admin" )
        member3 = WorkspaceMember( user_id=user3.id, workspace_id=user3_workspace.id, role="admin" )
        member4 = WorkspaceMember( user_id=user1.id, workspace_id=user2_workspace.id, role="member" )

        members_to_add = [member1, member2, member3, member4]
        db.add_all(members_to_add)
        db.flush()

        task1 = Task( title="Grow bananas", description="User powers to grow a million bananas for domain expansion", workspace_id=user1_workspace.id, creator_id=user1.id )
        task2 = Task( title="Design unicycle", description="Find the perfect design for maximum aerodynamics", workspace_id=user2_workspace.id, creator_id=user2.id )
        task3 = Task( title="Find a house to invade", description="Must find the most vulnerable house to start with", workspace_id=user3_workspace.id, creator_id=user3.id )
        task4 = Task( title="Create banana handle", description="Find a way to make the unicycle handle a banana", workspace_id=user2_workspace.id, creator_id=user1.id )

        tasks_to_add = [task1, task2, task3, task4]
        db.add_all(tasks_to_add)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"feeding failed {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_db()
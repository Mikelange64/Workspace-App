from sqlalchemy import select
from app.database import SessionLocal
from app.models import User


def promote_user(username: str):
    with SessionLocal() as db:
        stmt = select(User).where(User.username == username)
        user = db.execute(stmt).scalars().first()

        if not user:
            print(f"User '{username}' not found.")
            return

        user.is_superuser = True
        db.commit()
        print(f"Success! {username} is now a superuser.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        promote_user(sys.argv[1])
    else:
        print("Usage: python make_admin.py <username>")
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Resource, ResourceType
from app.utils import fetch_oembed_thumbnail


def backfill():
    with SessionLocal() as db:
        links = db.execute(
            select(Resource).where(
                Resource.type == ResourceType.LINK,
                Resource.thumbnail_url.is_(None),
            )
        ).scalars().all()

        updated = 0
        for link in links:
            thumbnail = fetch_oembed_thumbnail(link.url)
            if thumbnail:
                link.thumbnail_url = thumbnail
                updated += 1

        db.commit()
        print(f"Checked {len(links)} link(s) without a thumbnail, filled in {updated}.")


if __name__ == "__main__":
    backfill()

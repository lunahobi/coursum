from __future__ import annotations

from sqlalchemy import or_, select

from app.core.db import SessionLocal
from app.models.models import Course


def run() -> None:
    db = SessionLocal()
    try:
        courses = db.scalars(
            select(Course).where(
                Course.is_published.is_(True),
                or_(
                    Course.status == "draft",
                    Course.status == "",
                    Course.status.is_(None),
                ),
            )
        ).all()
        for course in courses:
            course.status = "published"
            db.add(course)
        db.commit()
        print(f"Updated courses: {len(courses)}")
    finally:
        db.close()


if __name__ == "__main__":
    run()

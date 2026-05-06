from __future__ import annotations

from copy import deepcopy

from app.core.db import SessionLocal
from app.core.text_repair import repair_text_payload
from app.models.models import (
    AnswerOption,
    Course,
    Lesson,
    Question,
    Recommendation,
    Result,
    Tenant,
    Test,
    Topic,
    User,
)


FIELDS_TO_REPAIR: dict[type, tuple[str, ...]] = {
    Tenant: ("name", "code"),
    User: ("full_name",),
    Course: ("title", "description"),
    Topic: ("title", "description"),
    Lesson: ("title", "summary", "content", "content_pages", "image_url", "video_url"),
    Test: ("title",),
    Question: ("text", "explanation"),
    AnswerOption: ("text",),
    Result: ("weak_topics",),
    Recommendation: ("text",),
}


def run() -> None:
    session = SessionLocal()
    updated_fields = 0
    updated_rows: set[tuple[str, int]] = set()

    try:
        for model, field_names in FIELDS_TO_REPAIR.items():
            for row in session.query(model).all():
                row_changed = False
                for field_name in field_names:
                    value = getattr(row, field_name)
                    repaired = repair_text_payload(deepcopy(value))
                    if repaired != value:
                        setattr(row, field_name, repaired)
                        updated_fields += 1
                        row_changed = True
                if row_changed:
                    updated_rows.add((model.__name__, row.id))

        session.commit()
        print(
            f"Text repair complete. Updated {updated_fields} fields across {len(updated_rows)} rows."
        )
    finally:
        session.close()


if __name__ == "__main__":
    run()

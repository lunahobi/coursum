from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import Assignment, Lesson


def _normalize_text(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _stable_page_id(lesson_id: int, raw_page_id: str | None, index: int) -> str:
    page_id = (raw_page_id or "").strip()
    return page_id or f"page-{lesson_id}-{index + 1}"


def _resolve_practice_page_id(lesson: Lesson) -> str | None:
    pages = lesson.content_pages or []
    if not pages:
        return None
    normalized_pages: list[dict[str, str | bool]] = []
    for index, page in enumerate(pages):
        title = _normalize_text(str(page.get("page_title") or ""))
        normalized_pages.append(
            {
                "page_id": _stable_page_id(lesson.id, str(page.get("page_id") or ""), index),
                "title": title,
                "is_practice": bool(page.get("is_practice")),
            }
        )
    for page in normalized_pages:
        if page["is_practice"]:
            return str(page["page_id"])
    for page in normalized_pages:
        if "практи" in str(page["title"]) or "practice" in str(page["title"]):
            return str(page["page_id"])
    return str(normalized_pages[-1]["page_id"])


@dataclass
class Counters:
    total: int = 0
    linked_by_lesson_id: int = 0
    linked_by_page_id: int = 0
    linked_by_title: int = 0
    skipped_no_lesson: int = 0
    unchanged: int = 0


def run() -> None:
    db = SessionLocal()
    counters = Counters()
    try:
        assignments = db.scalars(select(Assignment).order_by(Assignment.id.asc())).all()
        lessons = db.scalars(select(Lesson).order_by(Lesson.id.asc())).all()
        lessons_by_tenant_course: dict[tuple[int, int], list[Lesson]] = {}
        for lesson in lessons:
            lessons_by_tenant_course.setdefault((lesson.tenant_id, lesson.course_id), []).append(lesson)

        for assignment in assignments:
            counters.total += 1
            pool = lessons_by_tenant_course.get((assignment.tenant_id, assignment.course_id), [])
            if not pool:
                counters.skipped_no_lesson += 1
                continue

            matched_lesson: Lesson | None = None
            reason = ""

            if assignment.lesson_id:
                matched_lesson = next((lesson for lesson in pool if lesson.id == assignment.lesson_id), None)
                if matched_lesson:
                    reason = "lesson_id"

            if matched_lesson is None and assignment.page_id:
                target_page_id = assignment.page_id.strip()
                for lesson in pool:
                    pages = lesson.content_pages or []
                    if any(_stable_page_id(lesson.id, str(page.get("page_id") or ""), idx) == target_page_id for idx, page in enumerate(pages)):
                        matched_lesson = lesson
                        reason = "page_id"
                        break

            if matched_lesson is None:
                assignment_title = _normalize_text(assignment.title)
                if assignment_title:
                    for lesson in pool:
                        lesson_title = _normalize_text(lesson.title)
                        if (
                            lesson_title == assignment_title
                            or lesson_title.startswith(assignment_title)
                            or assignment_title.startswith(lesson_title)
                        ):
                            matched_lesson = lesson
                            reason = "title"
                            break

            if matched_lesson is None:
                counters.skipped_no_lesson += 1
                continue

            next_page_id = _resolve_practice_page_id(matched_lesson)
            changed = False
            if assignment.lesson_id != matched_lesson.id:
                assignment.lesson_id = matched_lesson.id
                changed = True
            if next_page_id and (assignment.page_id or "").strip() != next_page_id:
                assignment.page_id = next_page_id
                changed = True

            if not changed:
                counters.unchanged += 1
                continue

            db.add(assignment)
            if reason == "lesson_id":
                counters.linked_by_lesson_id += 1
            elif reason == "page_id":
                counters.linked_by_page_id += 1
            else:
                counters.linked_by_title += 1

        db.commit()
        print(
            "Backfill done:",
            f"total={counters.total}",
            f"updated_by_lesson_id={counters.linked_by_lesson_id}",
            f"updated_by_page_id={counters.linked_by_page_id}",
            f"updated_by_title={counters.linked_by_title}",
            f"unchanged={counters.unchanged}",
            f"skipped_no_lesson={counters.skipped_no_lesson}",
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()

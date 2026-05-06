from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import bleach
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Course, CourseSection, Enrollment, Lesson, LessonProgress, Membership, RoleName


SAFE_VIDEO_SUFFIXES = (".mp4", ".webm")
SAFE_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
ALLOWED_HTML_TAGS = [
    "p",
    "br",
    "div",
    "span",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "mark",
    "small",
    "code",
    "pre",
    "blockquote",
    "hr",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "a",
    "img",
    "video",
    "source",
]
ALLOWED_HTML_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
    "video": ["src", "poster", "controls", "preload", "playsinline"],
    "source": ["src", "type"],
}
ALLOWED_PROTOCOLS = ["http", "https"]
MISSING_MEDIA_ERROR = "Referenced media file is missing"


class _HtmlMediaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image_urls: list[str] = []
        self.video_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value for key, value in attrs}
        if tag == "img" and attr_map.get("src"):
            self.image_urls.append(attr_map["src"])
        if tag in {"video", "source"} and attr_map.get("src"):
            self.video_urls.append(attr_map["src"])


def is_safe_video_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https", ""}:
        return False
    return parsed.path.lower().endswith(SAFE_VIDEO_SUFFIXES)


def is_safe_image_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https", ""}:
        return False
    return parsed.path.lower().endswith(SAFE_IMAGE_SUFFIXES)


def _media_root() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "media"


def _media_url_exists(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme in {"http", "https"}:
        return True
    if not parsed.path.startswith("/media/"):
        return False
    filename = parsed.path.removeprefix("/media/")
    if not filename:
        return False
    return (_media_root() / filename).exists()


def _resolve_media_url(
    preferred_url: str | None,
    fallback_url: str | None,
    *,
    validator,
) -> str | None:
    for candidate in (preferred_url, fallback_url):
        if candidate and validator(candidate) and _media_url_exists(candidate):
            return candidate
    return preferred_url or fallback_url


def sanitize_html_fragment(raw_html: str | None) -> str:
    if not raw_html:
        return ""
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned.strip()


def _validate_html_media(html: str) -> None:
    parser = _HtmlMediaParser()
    parser.feed(html)
    for url in parser.video_urls:
        if not is_safe_video_url(url):
            raise HTTPException(status_code=422, detail="Only direct MP4/WebM video sources are supported")
    for url in parser.image_urls:
        if not is_safe_image_url(url):
            raise HTTPException(status_code=422, detail="Only direct PNG/JPG/WebP/GIF image sources are supported")


def sanitize_content_pages(content_pages: list[dict] | None) -> list[dict] | None:
    if content_pages is None:
        return None
    sanitized_pages: list[dict] = []
    for page_index, page in enumerate(content_pages):
        blocks: list[dict] = []
        for raw_block in page.get("blocks", []):
            block_type = raw_block.get("type", "text")
            if block_type == "html":
                html = sanitize_html_fragment(raw_block.get("html") or raw_block.get("text"))
                if html:
                    _validate_html_media(html)
                    blocks.append({"type": "html", "html": html})
            elif block_type == "text":
                text = (raw_block.get("text") or "").strip()
                if text:
                    blocks.append({"type": "text", "text": text})
            elif block_type == "image":
                url = (raw_block.get("url") or "").strip()
                if url:
                    if not is_safe_image_url(url):
                        raise HTTPException(status_code=422, detail="Only direct PNG/JPG/WebP/GIF image sources are supported")
                    blocks.append(
                        {
                            "type": "image",
                            "url": url,
                            "alt": raw_block.get("alt") or page.get("page_title") or f"Page {page_index + 1}",
                        }
                    )
            elif block_type == "video":
                url = (raw_block.get("url") or "").strip()
                if url:
                    if not is_safe_video_url(url):
                        raise HTTPException(status_code=422, detail="Only direct MP4/WebM video sources are supported")
                    blocks.append(
                        {
                            "type": "video",
                            "url": url,
                            "title": raw_block.get("title") or page.get("page_title") or f"Page {page_index + 1}",
                        }
                    )
        sanitized_pages.append(
            {
                "page_id": page.get("page_id") or f"page-{page_index + 1}",
                "chapter_title": (page.get("chapter_title") or "").strip() or f"Chapter {page_index + 1}",
                "page_title": (page.get("page_title") or "").strip() or f"Page {page_index + 1}",
                "blocks": blocks,
            }
        )
    return sanitized_pages


def validate_lesson_media(summary_video_url: str | None, content_pages: list[dict] | None) -> None:
    if summary_video_url and not is_safe_video_url(summary_video_url):
        raise HTTPException(status_code=422, detail="Only direct MP4/WebM video sources are supported")
    for page in content_pages or []:
        for block in page.get("blocks", []):
            if block.get("type") == "video":
                if not is_safe_video_url(block.get("url")):
                    raise HTTPException(status_code=422, detail="Only direct MP4/WebM video sources are supported")
            if block.get("type") == "html":
                _validate_html_media(block.get("html") or block.get("text") or "")


def legacy_pages_for_lesson(lesson: Lesson) -> list[dict]:
    pages: list[dict] = []
    intro_blocks: list[dict] = []
    if lesson.summary:
        intro_blocks.append({"type": "text", "text": lesson.summary})
    if lesson.image_url:
        intro_blocks.append({"type": "image", "url": lesson.image_url, "alt": lesson.title})
    if lesson.video_url:
        valid_video = is_safe_video_url(lesson.video_url)
        available_video = _media_url_exists(lesson.video_url)
        intro_blocks.append(
            {
                "type": "video",
                "url": lesson.video_url,
                "title": "Lesson video",
                "status": "ready" if valid_video and available_video else "invalid",
                "error": None
                if valid_video and available_video
                else "Only direct MP4/WebM video sources are supported"
                if not valid_video
                else MISSING_MEDIA_ERROR,
            }
        )

    current_title: str | None = None
    current_lines: list[str] = []
    page_index = 0
    for raw_line in lesson.content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            if current_title is not None:
                pages.append(
                    {
                        "page_id": f"lesson-{lesson.id}-page-{page_index}",
                        "chapter_title": lesson.title,
                        "page_title": current_title,
                        "blocks": [{"type": "text", "text": "\n".join(current_lines).strip()}],
                    }
                )
                page_index += 1
            current_title = line[3:].strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_title is not None:
        pages.append(
            {
                "page_id": f"lesson-{lesson.id}-page-{page_index}",
                "chapter_title": lesson.title,
                "page_title": current_title,
                "blocks": [{"type": "text", "text": "\n".join(current_lines).strip()}],
            }
        )
    elif lesson.content.strip() or intro_blocks:
        pages.append(
            {
                "page_id": f"lesson-{lesson.id}-page-0",
                "chapter_title": lesson.title,
                "page_title": lesson.title,
                "blocks": intro_blocks + ([{"type": "text", "text": lesson.content.strip()}] if lesson.content.strip() else []),
            }
        )

    if intro_blocks and pages:
        pages[0]["blocks"] = intro_blocks + pages[0]["blocks"]
    return pages or [
        {
            "page_id": f"lesson-{lesson.id}-page-0",
            "chapter_title": lesson.title,
            "page_title": lesson.title,
            "blocks": [{"type": "text", "text": lesson.summary or lesson.title}],
        }
    ]


def normalize_pages(lesson: Lesson) -> list[dict]:
    raw_pages = lesson.content_pages or legacy_pages_for_lesson(lesson)
    normalized: list[dict] = []
    for index, raw_page in enumerate(raw_pages):
        blocks: list[dict] = []
        for raw_block in raw_page.get("blocks", []):
            block_type = raw_block.get("type", "text")
            if block_type == "text":
                text = (raw_block.get("text") or "").strip()
                if text:
                    blocks.append({"type": "text", "text": text})
            elif block_type == "html":
                html = sanitize_html_fragment(raw_block.get("html") or raw_block.get("text"))
                if html:
                    blocks.append({"type": "html", "html": html})
            elif block_type == "image":
                url = _resolve_media_url(
                    raw_block.get("url"),
                    lesson.image_url,
                    validator=is_safe_image_url,
                )
                if url:
                    blocks.append({"type": "image", "url": url, "alt": raw_block.get("alt") or raw_page.get("page_title") or lesson.title})
            elif block_type == "video":
                url = _resolve_media_url(
                    raw_block.get("url"),
                    lesson.video_url,
                    validator=is_safe_video_url,
                )
                valid = is_safe_video_url(url)
                available = _media_url_exists(url)
                blocks.append(
                    {
                        "type": "video",
                        "url": url,
                        "title": raw_block.get("title") or raw_page.get("page_title") or lesson.title,
                        "status": "ready" if valid and available else "invalid",
                        "error": None
                        if valid and available
                        else "Only direct MP4/WebM video sources are supported"
                        if not valid
                        else MISSING_MEDIA_ERROR,
                    }
                )
        if not blocks:
            blocks = [{"type": "text", "text": raw_page.get("page_title") or lesson.title}]
        normalized.append(
            {
                "page_id": raw_page.get("page_id") or f"lesson-{lesson.id}-page-{index}",
                "chapter_title": raw_page.get("chapter_title") or lesson.title,
                "page_title": raw_page.get("page_title") or f"Page {index + 1}",
                "blocks": blocks,
            }
        )
    return normalized


def ensure_course_access(db: Session, membership: Membership, course_id: int) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.tenant_id == membership.tenant_id))
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if membership.role.name == RoleName.learner.value:
        enrollment = db.scalar(select(Enrollment).where(Enrollment.tenant_id == membership.tenant_id, Enrollment.course_id == course.id, Enrollment.user_id == membership.user_id))
        if enrollment is None:
            raise HTTPException(status_code=403, detail="Enrollment required")
    return course


def recalculate_enrollment_progress(db: Session, tenant_id: int, user_id: int, course_id: int) -> Enrollment | None:
    enrollment = db.scalar(select(Enrollment).where(Enrollment.tenant_id == tenant_id, Enrollment.user_id == user_id, Enrollment.course_id == course_id))
    if enrollment is None:
        return None
    lesson_ids = [
        item.id
        for item in db.scalars(
            select(Lesson).where(
                Lesson.tenant_id == tenant_id,
                Lesson.course_id == course_id,
                Lesson.is_visible.is_(True),
                Lesson.is_published.is_(True),
            )
        ).all()
    ]
    total_lessons = len(lesson_ids) or 1
    completed_lessons = db.scalars(
        select(LessonProgress.lesson_id).where(
            LessonProgress.tenant_id == tenant_id,
            LessonProgress.user_id == user_id,
            LessonProgress.course_id == course_id,
            LessonProgress.is_completed.is_(True),
        )
    ).all()
    enrollment.progress_percent = int((len(set(completed_lessons)) / total_lessons) * 100)
    enrollment.completed = len(set(completed_lessons)) >= total_lessons
    return enrollment


def build_course_outline(db: Session, membership: Membership, course_id: int, active_lesson_id: int | None = None) -> dict:
    course = ensure_course_access(db, membership, course_id)
    section_query = select(CourseSection).where(
        CourseSection.tenant_id == membership.tenant_id,
        CourseSection.course_id == course.id,
    )
    if membership.role.name == RoleName.learner.value:
        section_query = section_query.where(CourseSection.is_visible.is_(True))
    sections = db.scalars(section_query.order_by(CourseSection.sort_order, CourseSection.id)).all()
    visible_section_ids = {section.id for section in sections}

    lesson_query = select(Lesson).where(Lesson.tenant_id == membership.tenant_id, Lesson.course_id == course.id)
    if membership.role.name == RoleName.learner.value:
        lesson_query = lesson_query.where(Lesson.is_visible.is_(True), Lesson.is_published.is_(True))
        if visible_section_ids:
            lesson_query = lesson_query.where((Lesson.section_id.is_(None)) | Lesson.section_id.in_(visible_section_ids))
        else:
            lesson_query = lesson_query.where(Lesson.section_id.is_(None))
    lessons = db.scalars(lesson_query.order_by(Lesson.sort_order, Lesson.id)).all()
    progress_rows = db.scalars(
        select(LessonProgress).where(
            LessonProgress.tenant_id == membership.tenant_id,
            LessonProgress.user_id == membership.user_id,
            LessonProgress.course_id == course.id,
        )
    ).all()
    progress_map = {row.lesson_id: row for row in progress_rows}
    incomplete_rows = [row for row in progress_rows if not row.is_completed]
    resume_lesson_id = active_lesson_id
    if resume_lesson_id is None and incomplete_rows:
        resume_lesson_id = max(incomplete_rows, key=lambda row: row.updated_at).lesson_id
    if resume_lesson_id is None:
        for lesson in lessons:
            row = progress_map.get(lesson.id)
            if row is None or not row.is_completed:
                resume_lesson_id = lesson.id
                break
    if resume_lesson_id is None and lessons:
        resume_lesson_id = lessons[0].id

    lesson_items: list[dict] = []
    completed_lessons = 0
    for lesson in lessons:
        pages = normalize_pages(lesson)
        row = progress_map.get(lesson.id)
        is_completed = bool(row and row.is_completed)
        if is_completed:
            completed_lessons += 1
        has_video = any(block.get("type") == "video" and block.get("status") == "ready" for page in pages for block in page["blocks"])
        lesson_items.append(
            {
                "id": lesson.id,
                "section_id": lesson.section_id,
                "title": lesson.title,
                "summary": lesson.summary,
                "sort_order": lesson.sort_order,
                "duration_minutes": lesson.duration_minutes,
                "page_count": len(pages),
                "current_page_index": row.current_page_index if row else 0,
                "is_completed": is_completed,
                "is_current": lesson.id == resume_lesson_id,
                "has_video": has_video,
            }
        )

    total_lessons = len(lessons) or 1
    return {
        "course_id": course.id,
        "course_title": course.title,
        "description": course.description,
        "total_lessons": len(lessons),
        "completed_lessons": completed_lessons,
        "progress_percent": int((completed_lessons / total_lessons) * 100) if lessons else 0,
        "resume_lesson_id": resume_lesson_id,
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
            }
            for section in sections
        ],
        "lessons": lesson_items,
    }


def build_lesson_player(db: Session, membership: Membership, lesson_id: int) -> dict:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == membership.tenant_id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if membership.role.name == RoleName.learner.value and (not lesson.is_visible or not lesson.is_published):
        raise HTTPException(status_code=404, detail="Lesson not available")
    course = ensure_course_access(db, membership, lesson.course_id)
    pages = normalize_pages(lesson)
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.tenant_id == membership.tenant_id,
            LessonProgress.user_id == membership.user_id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    outline = build_course_outline(db, membership, lesson.course_id, active_lesson_id=lesson.id)
    lesson_order = [item["id"] for item in outline["lessons"]]
    current_index = lesson_order.index(lesson.id)
    chapters: dict[str, list[dict]] = {}
    for index, page in enumerate(pages):
        chapters.setdefault(page["chapter_title"], []).append({"page_id": page["page_id"], "page_title": page["page_title"], "page_index": index})
    current_page_index = 0 if progress is None else max(0, min(progress.current_page_index, len(pages) - 1))
    return {
        "course_id": lesson.course_id,
        "course_title": course.title,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "summary": lesson.summary,
        "duration_minutes": lesson.duration_minutes,
        "pages": pages,
        "chapters": [{"chapter_title": title, "pages": items} for title, items in chapters.items()],
        "outline": outline,
        "state": {
            "current_page_index": current_page_index,
            "completed_page_ids": [] if progress is None else progress.completed_page_ids,
            "is_completed": False if progress is None else progress.is_completed,
            "last_video_position_seconds": 0 if progress is None else progress.last_video_position_seconds,
        },
        "previous_lesson_id": lesson_order[current_index - 1] if current_index > 0 else None,
        "next_lesson_id": lesson_order[current_index + 1] if current_index < len(lesson_order) - 1 else None,
    }


def save_lesson_state(
    db: Session,
    membership: Membership,
    lesson_id: int,
    *,
    current_page_index: int | None,
    completed_page_ids: list[str] | None,
    last_video_position_seconds: int | None,
    is_completed: bool | None,
) -> dict:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == membership.tenant_id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    ensure_course_access(db, membership, lesson.course_id)
    pages = normalize_pages(lesson)
    valid_page_ids = {page["page_id"] for page in pages}
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.tenant_id == membership.tenant_id,
            LessonProgress.user_id == membership.user_id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        progress = LessonProgress(
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            current_page_index=0,
            completed_page_ids=[],
            is_completed=False,
            last_video_position_seconds=0,
        )
        db.add(progress)
        db.flush()

    if current_page_index is not None:
        progress.current_page_index = max(0, min(current_page_index, len(pages) - 1))
    if completed_page_ids is not None:
        deduped = [page_id for page_id in completed_page_ids if page_id in valid_page_ids]
        progress.completed_page_ids = list(dict.fromkeys(deduped))
    if last_video_position_seconds is not None:
        progress.last_video_position_seconds = max(0, last_video_position_seconds)

    progress.is_completed = bool(is_completed) or len(set(progress.completed_page_ids)) >= len(valid_page_ids)
    progress.updated_at = datetime.utcnow()
    db.flush()
    enrollment = recalculate_enrollment_progress(db, membership.tenant_id, membership.user_id, lesson.course_id)
    db.commit()
    return {
        "current_page_index": progress.current_page_index,
        "completed_page_ids": progress.completed_page_ids,
        "is_completed": progress.is_completed,
        "last_video_position_seconds": progress.last_video_position_seconds,
        "progress_percent": 0 if enrollment is None else enrollment.progress_percent,
        "course_completed": False if enrollment is None else enrollment.completed,
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.models.models import Course, CourseSection, Lesson, LessonProgress, Membership, Recommendation, RoleName, Tenant, Topic
from app.schemas.course import (
    LessonCreate,
    LessonFlagUpdate,
    LessonPlayerRead,
    LessonRead,
    LessonReorderRequest,
    LessonStateUpdate,
    LessonUpdate,
)
from app.services.lesson_player import (
    build_lesson_player,
    normalize_pages,
    sanitize_content_pages,
    save_lesson_state,
    validate_lesson_media,
)

router = APIRouter(tags=["lessons"])


def _require_course_in_tenant(db: Session, tenant_id: int, course_id: int) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.tenant_id == tenant_id))
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _require_topic_in_tenant(db: Session, tenant_id: int, topic_id: int | None) -> None:
    if topic_id is None:
        return
    topic = db.scalar(select(Topic.id).where(Topic.id == topic_id, Topic.tenant_id == tenant_id))
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")


def _require_section_in_course(db: Session, tenant_id: int, course_id: int, section_id: int) -> CourseSection:
    section = db.scalar(
        select(CourseSection).where(
            CourseSection.id == section_id,
            CourseSection.tenant_id == tenant_id,
            CourseSection.course_id == course_id,
        )
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@router.get("/lessons", response_model=list[LessonRead])
def list_lessons(course_id: int, membership: Membership = Depends(active_membership), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> list[LessonRead]:
    _require_course_in_tenant(db, tenant.id, course_id)
    query = select(Lesson).where(Lesson.tenant_id == tenant.id, Lesson.course_id == course_id)
    if membership.role.name == RoleName.learner.value:
        query = query.where(Lesson.is_visible.is_(True), Lesson.is_published.is_(True))
    lessons = db.scalars(query.order_by(Lesson.section_id.is_(None), Lesson.section_id, Lesson.sort_order, Lesson.id)).all()
    return [LessonRead.model_validate(item) for item in lessons]


@router.post("/lessons", response_model=LessonRead)
def create_lesson(
    payload: LessonCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonRead:
    _require_course_in_tenant(db, tenant.id, payload.course_id)
    _require_topic_in_tenant(db, tenant.id, payload.topic_id)
    if payload.section_id is not None:
        _require_section_in_course(db, tenant.id, payload.course_id, payload.section_id)
    content_pages = sanitize_content_pages(None if payload.content_pages is None else [page.model_dump() for page in payload.content_pages])
    validate_lesson_media(payload.video_url, content_pages)
    lesson = Lesson(
        tenant_id=tenant.id,
        course_id=payload.course_id,
        section_id=payload.section_id,
        topic_id=payload.topic_id,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        content_pages=content_pages,
        duration_minutes=payload.duration_minutes,
        image_url=payload.image_url,
        video_url=payload.video_url,
        is_visible=payload.is_visible,
        is_published=payload.is_published,
        sort_order=payload.sort_order,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    write_audit_log(db, action="lessons.create", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="lesson", entity_id=lesson.id, details=payload.title)
    db.commit()
    return LessonRead.model_validate(lesson)


@router.patch("/lessons/{lesson_id}", response_model=LessonRead)
def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _require_course_in_tenant(db, tenant.id, payload.course_id)
    _require_topic_in_tenant(db, tenant.id, payload.topic_id)
    if payload.section_id is not None:
        _require_section_in_course(db, tenant.id, payload.course_id, payload.section_id)
    content_pages = sanitize_content_pages(None if payload.content_pages is None else [page.model_dump() for page in payload.content_pages])
    validate_lesson_media(payload.video_url, content_pages)
    lesson.course_id = payload.course_id
    lesson.section_id = payload.section_id
    lesson.topic_id = payload.topic_id
    lesson.title = payload.title
    lesson.summary = payload.summary
    lesson.content = payload.content
    lesson.content_pages = content_pages
    lesson.duration_minutes = payload.duration_minutes
    lesson.image_url = payload.image_url
    lesson.video_url = payload.video_url
    lesson.is_visible = payload.is_visible
    lesson.is_published = payload.is_published
    lesson.sort_order = payload.sort_order
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    write_audit_log(db, action="lessons.update", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="lesson", entity_id=lesson.id, details=payload.title)
    db.commit()
    return LessonRead.model_validate(lesson)


@router.post("/courses/{course_id}/lessons/reorder")
def reorder_lessons(
    course_id: int,
    payload: LessonReorderRequest,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    _require_course_in_tenant(db, tenant.id, course_id)
    lessons = db.scalars(select(Lesson).where(Lesson.tenant_id == tenant.id, Lesson.course_id == course_id)).all()
    indexed = {item.id: item for item in lessons}
    for index, lesson_id in enumerate(payload.lesson_ids):
        lesson = indexed.get(lesson_id)
        if lesson is None:
            continue
        lesson.sort_order = index + 1
        db.add(lesson)
    db.commit()
    write_audit_log(
        db,
        action="lessons.reorder",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course_id,
    )
    db.commit()
    return {"updated": len(payload.lesson_ids)}


@router.post("/lessons/{lesson_id}/duplicate", response_model=LessonRead)
def duplicate_lesson(
    lesson_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    copy = Lesson(
        tenant_id=tenant.id,
        course_id=lesson.course_id,
        section_id=lesson.section_id,
        topic_id=lesson.topic_id,
        title=f"{lesson.title} (copy)",
        summary=lesson.summary,
        content=lesson.content,
        content_pages=lesson.content_pages,
        duration_minutes=lesson.duration_minutes,
        image_url=lesson.image_url,
        video_url=lesson.video_url,
        is_visible=lesson.is_visible,
        is_published=False,
        sort_order=lesson.sort_order + 1,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    write_audit_log(
        db,
        action="lessons.duplicate",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="lesson",
        entity_id=copy.id,
        details=copy.title,
    )
    db.commit()
    return LessonRead.model_validate(copy)


@router.patch("/lessons/{lesson_id}/visibility", response_model=LessonRead)
def set_lesson_visibility(
    lesson_id: int,
    payload: LessonFlagUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson.is_visible = payload.value
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    write_audit_log(
        db,
        action="lessons.visibility",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="lesson",
        entity_id=lesson.id,
        details=str(payload.value),
    )
    db.commit()
    return LessonRead.model_validate(lesson)


@router.patch("/lessons/{lesson_id}/publication", response_model=LessonRead)
def set_lesson_publication(
    lesson_id: int,
    payload: LessonFlagUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson.is_published = payload.value
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    write_audit_log(
        db,
        action="lessons.publication",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="lesson",
        entity_id=lesson.id,
        details=str(payload.value),
    )
    db.commit()
    return LessonRead.model_validate(lesson)


@router.delete("/lessons/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    db.execute(delete(LessonProgress).where(LessonProgress.tenant_id == tenant.id, LessonProgress.lesson_id == lesson.id))
    db.execute(delete(Recommendation).where(Recommendation.tenant_id == tenant.id, Recommendation.lesson_id == lesson.id))
    db.execute(delete(Lesson).where(Lesson.id == lesson.id, Lesson.tenant_id == tenant.id))
    db.commit()
    write_audit_log(
        db,
        action="lessons.delete",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="lesson",
        entity_id=lesson.id,
        details=lesson.title,
    )
    db.commit()
    return {"deleted": True, "lesson_id": lesson.id}


@router.get("/lessons/{lesson_id}/player", response_model=LessonPlayerRead)
def get_lesson_player(
    lesson_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> LessonPlayerRead:
    if membership.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if membership.role.name == RoleName.learner.value and (not lesson.is_visible or not lesson.is_published):
        raise HTTPException(status_code=404, detail="Lesson not available")
    return LessonPlayerRead.model_validate(build_lesson_player(db, membership, lesson_id))


@router.post("/lessons/{lesson_id}/state")
def update_lesson_state(
    lesson_id: int,
    payload: LessonStateUpdate,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    if membership.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return save_lesson_state(
        db,
        membership,
        lesson_id,
        current_page_index=payload.current_page_index,
        completed_page_ids=payload.completed_page_ids,
        last_video_position_seconds=payload.last_video_position_seconds,
        is_completed=payload.is_completed,
    )


@router.post("/lessons/{lesson_id}/progress")
def mark_lesson_progress(
    lesson_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    page_ids = [page["page_id"] for page in normalize_pages(lesson)]
    return save_lesson_state(
        db,
        membership,
        lesson_id,
        current_page_index=max(0, len(page_ids) - 1),
        completed_page_ids=page_ids,
        last_video_position_seconds=None,
        is_completed=True,
    )

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.models.models import (
    AnswerOption,
    Assignment,
    AssignmentSubmission,
    AssignmentSubmissionFile,
    Attempt,
    AttemptAnswer,
    Course,
    CourseAssignment,
    CourseRecommendation,
    CourseSection,
    CourseStaffAssignment,
    EditorRecommendation,
    Enrollment,
    Group,
    GroupMember,
    Lesson,
    LessonProgress,
    Membership,
    Question,
    QuestionTopic,
    Recommendation,
    Result,
    Role,
    RoleName,
    SubmissionReview,
    Tenant,
    Test,
    Topic,
    User,
)
from app.schemas.assignment import CourseAssignmentRead
from app.schemas.course import (
    AssignmentRequest,
    CourseCreate,
    CourseOutlineRead,
    CourseRead,
    CourseStatusUpdate,
    CourseUpdate,
    SectionCreate,
    SectionRead,
    SectionReorderRequest,
    SectionUpdate,
    StaffAssignmentRequest,
)
from app.services.lesson_player import (
    build_course_outline,
)
from app.services.notifications import send_mock_notification

router = APIRouter(tags=["courses"])
COURSE_STATUSES = {"draft", "published", "archived"}
STAFF_ROLE_NAMES = {RoleName.teacher.value, RoleName.org_admin.value, RoleName.system_admin.value}


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


def _require_user_membership_in_tenant(db: Session, tenant_id: int, user_id: int) -> None:
    membership = db.scalar(
        select(Membership.id).where(
            Membership.tenant_id == tenant_id,
            Membership.user_id == user_id,
            Membership.is_active.is_(True),
        )
    )
    if membership is None:
        raise HTTPException(status_code=422, detail="User must belong to the current tenant")


def _effective_user_ids_for_assignment(db: Session, tenant_id: int, assignment: CourseAssignment) -> list[int]:
    if assignment.user_id is not None:
        return [assignment.user_id]
    if assignment.group_id is None:
        return []
    return list(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.tenant_id == tenant_id,
                GroupMember.group_id == assignment.group_id,
            )
        ).all()
    )


def _has_course_assignment_access(db: Session, tenant_id: int, course_id: int, user_id: int) -> bool:
    direct_assignment = db.scalar(
        select(CourseAssignment.id).where(
            CourseAssignment.tenant_id == tenant_id,
            CourseAssignment.course_id == course_id,
            CourseAssignment.user_id == user_id,
        )
    )
    if direct_assignment is not None:
        return True

    group_ids = list(
        db.scalars(
            select(GroupMember.group_id).where(
                GroupMember.tenant_id == tenant_id,
                GroupMember.user_id == user_id,
            )
        ).all()
    )
    if not group_ids:
        return False
    legacy_group_assignment = db.scalar(
        select(CourseAssignment.id).where(
            CourseAssignment.tenant_id == tenant_id,
            CourseAssignment.course_id == course_id,
            CourseAssignment.user_id.is_(None),
            CourseAssignment.group_id.in_(group_ids),
        )
    )
    return legacy_group_assignment is not None


def _normalize_course_status(value: str | None) -> str:
    normalized = (value or "draft").strip().lower()
    if normalized not in COURSE_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported course status")
    return normalized


def _sync_course_publication_flag(course: Course, status_value: str) -> None:
    course.status = status_value
    course.is_published = status_value == "published"


def _section_read(section: CourseSection) -> SectionRead:
    return SectionRead.model_validate(section)


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


def _course_read(course: Course, image_url: str | None = None) -> CourseRead:
    return CourseRead(
        id=course.id,
        title=course.title,
        description=course.description,
        is_published=course.is_published,
        status=course.status or ("published" if course.is_published else "draft"),
        image_url=image_url,
        category=course.category,
        access_settings=course.access_settings or {},
        available_from=course.available_from,
        available_to=course.available_to,
    )


def _default_course_cover(course: Course, tenant_locale: str) -> str | None:
    suffix = "ru" if tenant_locale.lower().startswith("ru") else "en"
    normalized = course.title.lower()
    if "онбординг" in normalized or "onboarding" in normalized:
        return f"/media/onboarding-cover-{suffix}.png"
    if "безопас" in normalized or "security" in normalized:
        return f"/media/security-cover-{suffix}.png"
    if "сервис" in normalized or "service" in normalized or "client" in normalized:
        return f"/media/service-cover-{suffix}.png"
    return None


def _course_cover_map(
    db: Session,
    tenant_id: int,
    tenant_locale: str,
    courses: list[Course],
) -> dict[int, str]:
    if not courses:
        return {}
    cover_map: dict[int, str] = {}
    remaining_course_ids: list[int] = []
    for course in courses:
        if course.image_url:
            cover_map[course.id] = course.image_url
            continue
        default_cover = _default_course_cover(course, tenant_locale)
        if default_cover is not None:
            cover_map[course.id] = default_cover
        else:
            remaining_course_ids.append(course.id)
    if not remaining_course_ids:
        return cover_map
    lessons = db.scalars(
        select(Lesson)
        .where(
            Lesson.tenant_id == tenant_id,
            Lesson.course_id.in_(remaining_course_ids),
            Lesson.image_url.is_not(None),
        )
        .order_by(Lesson.course_id, Lesson.sort_order, Lesson.id)
    ).all()
    for lesson in lessons:
        if lesson.image_url:
            cover_map.setdefault(lesson.course_id, lesson.image_url)
    return cover_map


def _delete_course_dependencies(db: Session, tenant_id: int, course_id: int) -> dict[str, int]:
    lesson_ids = db.scalars(select(Lesson.id).where(Lesson.tenant_id == tenant_id, Lesson.course_id == course_id)).all()
    section_ids = db.scalars(select(CourseSection.id).where(CourseSection.tenant_id == tenant_id, CourseSection.course_id == course_id)).all()
    test_ids = db.scalars(select(Test.id).where(Test.tenant_id == tenant_id, Test.course_id == course_id)).all()
    assignment_ids = db.scalars(select(Assignment.id).where(Assignment.tenant_id == tenant_id, Assignment.course_id == course_id)).all()
    submission_ids = (
        db.scalars(
            select(AssignmentSubmission.id).where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.assignment_id.in_(assignment_ids),
            )
        ).all()
        if assignment_ids
        else []
    )
    question_ids = (
        db.scalars(select(Question.id).where(Question.tenant_id == tenant_id, Question.test_id.in_(test_ids))).all() if test_ids else []
    )
    attempt_ids = (
        db.scalars(select(Attempt.id).where(Attempt.tenant_id == tenant_id, Attempt.test_id.in_(test_ids))).all() if test_ids else []
    )
    result_ids = (
        db.scalars(
            select(Result.id)
            .join(Attempt, Attempt.id == Result.attempt_id)
            .where(Result.tenant_id == tenant_id, Attempt.tenant_id == tenant_id, Attempt.test_id.in_(test_ids))
        ).all()
        if test_ids
        else []
    )

    if result_ids:
        db.execute(delete(Recommendation).where(Recommendation.tenant_id == tenant_id, Recommendation.result_id.in_(result_ids)))
    if lesson_ids:
        db.execute(delete(Recommendation).where(Recommendation.tenant_id == tenant_id, Recommendation.lesson_id.in_(lesson_ids)))

    if submission_ids:
        db.execute(
            delete(AssignmentSubmissionFile).where(
                AssignmentSubmissionFile.tenant_id == tenant_id,
                AssignmentSubmissionFile.submission_id.in_(submission_ids),
            )
        )
        db.execute(
            delete(SubmissionReview).where(
                SubmissionReview.tenant_id == tenant_id,
                SubmissionReview.submission_id.in_(submission_ids),
            )
        )
        db.execute(
            delete(AssignmentSubmission).where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.id.in_(submission_ids),
            )
        )
    if assignment_ids:
        db.execute(delete(Assignment).where(Assignment.tenant_id == tenant_id, Assignment.id.in_(assignment_ids)))

    if attempt_ids:
        db.execute(delete(AttemptAnswer).where(AttemptAnswer.tenant_id == tenant_id, AttemptAnswer.attempt_id.in_(attempt_ids)))
        db.execute(delete(Result).where(Result.tenant_id == tenant_id, Result.attempt_id.in_(attempt_ids)))
        db.execute(delete(Attempt).where(Attempt.tenant_id == tenant_id, Attempt.id.in_(attempt_ids)))

    if question_ids:
        db.execute(delete(QuestionTopic).where(QuestionTopic.tenant_id == tenant_id, QuestionTopic.question_id.in_(question_ids)))
        db.execute(delete(AnswerOption).where(AnswerOption.question_id.in_(question_ids)))
        db.execute(delete(Question).where(Question.tenant_id == tenant_id, Question.id.in_(question_ids)))

    if test_ids:
        db.execute(delete(Test).where(Test.tenant_id == tenant_id, Test.id.in_(test_ids)))

    db.execute(delete(LessonProgress).where(LessonProgress.tenant_id == tenant_id, LessonProgress.course_id == course_id))
    db.execute(delete(CourseAssignment).where(CourseAssignment.tenant_id == tenant_id, CourseAssignment.course_id == course_id))
    db.execute(delete(CourseStaffAssignment).where(CourseStaffAssignment.tenant_id == tenant_id, CourseStaffAssignment.course_id == course_id))
    db.execute(delete(EditorRecommendation).where(EditorRecommendation.tenant_id == tenant_id, EditorRecommendation.course_id == course_id))
    db.execute(delete(CourseRecommendation).where(CourseRecommendation.tenant_id == tenant_id, CourseRecommendation.course_id == course_id))
    db.execute(delete(Enrollment).where(Enrollment.tenant_id == tenant_id, Enrollment.course_id == course_id))

    if lesson_ids:
        db.execute(delete(EditorRecommendation).where(EditorRecommendation.tenant_id == tenant_id, EditorRecommendation.lesson_id.in_(lesson_ids)))
        db.execute(delete(Lesson).where(Lesson.tenant_id == tenant_id, Lesson.id.in_(lesson_ids)))
    if section_ids:
        db.execute(delete(CourseSection).where(CourseSection.tenant_id == tenant_id, CourseSection.id.in_(section_ids)))

    return {
        "deleted_lessons": len(lesson_ids),
        "deleted_tests": len(test_ids),
        "deleted_sections": len(section_ids),
        "deleted_assignments": len(assignment_ids),
        "deleted_submissions": len(submission_ids),
    }


def _course_dependency_impact(db: Session, tenant_id: int, course_id: int) -> dict[str, int]:
    lesson_ids = db.scalars(select(Lesson.id).where(Lesson.tenant_id == tenant_id, Lesson.course_id == course_id)).all()
    test_ids = db.scalars(select(Test.id).where(Test.tenant_id == tenant_id, Test.course_id == course_id)).all()
    assignment_ids = db.scalars(select(Assignment.id).where(Assignment.tenant_id == tenant_id, Assignment.course_id == course_id)).all()
    return {
        "lessons": len(lesson_ids),
        "tests": len(test_ids),
        "assignments": len(assignment_ids),
        "enrollments": len(
            db.scalars(select(Enrollment.id).where(Enrollment.tenant_id == tenant_id, Enrollment.course_id == course_id)).all()
        ),
        "staff_links": len(
            db.scalars(select(CourseStaffAssignment.id).where(CourseStaffAssignment.tenant_id == tenant_id, CourseStaffAssignment.course_id == course_id)).all()
        ),
    }


@router.get("/courses", response_model=list[CourseRead])
def list_courses(membership: Membership = Depends(active_membership), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> list[CourseRead]:
    if membership.role.name == RoleName.learner.value:
        courses = db.scalars(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(
                Course.tenant_id == tenant.id,
                Enrollment.user_id == membership.user_id,
                Course.status == "published",
            )
        ).all()
    else:
        courses = db.scalars(select(Course).where(Course.tenant_id == tenant.id)).all()
    cover_map = _course_cover_map(db, tenant.id, tenant.locale, courses)
    return [_course_read(course, cover_map.get(course.id)) for course in courses]


@router.post("/courses", response_model=CourseRead)
def create_course(
    payload: CourseCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    status_value = _normalize_course_status(payload.status)
    course = Course(
        tenant_id=tenant.id,
        title=payload.title,
        description=payload.description,
        image_url=payload.image_url,
        category=payload.category,
        access_settings=payload.access_settings or {},
        available_from=payload.available_from,
        available_to=payload.available_to,
        created_by_id=membership.user_id,
    )
    _sync_course_publication_flag(course, status_value)
    db.add(course)
    db.commit()
    db.refresh(course)
    write_audit_log(db, action="courses.create", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="course", entity_id=course.id, details=payload.title)
    db.commit()
    cover_map = _course_cover_map(db, tenant.id, tenant.locale, [course])
    return _course_read(course, cover_map.get(course.id))


@router.get("/courses/{course_id}", response_model=CourseRead)
def get_course(course_id: int, _: Membership = Depends(active_membership), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> CourseRead:
    course = _require_course_in_tenant(db, tenant.id, course_id)
    cover_map = _course_cover_map(db, tenant.id, tenant.locale, [course])
    return _course_read(course, cover_map.get(course.id))


@router.patch("/courses/{course_id}", response_model=CourseRead)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = _require_course_in_tenant(db, tenant.id, course_id)
    status_value = _normalize_course_status(payload.status)
    course.title = payload.title
    course.description = payload.description
    course.image_url = payload.image_url
    course.category = payload.category
    course.access_settings = payload.access_settings or {}
    course.available_from = payload.available_from
    course.available_to = payload.available_to
    _sync_course_publication_flag(course, status_value)
    db.add(course)
    db.commit()
    db.refresh(course)
    write_audit_log(
        db,
        action="courses.update",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course.id,
        details=payload.title,
    )
    db.commit()
    cover_map = _course_cover_map(db, tenant.id, tenant.locale, [course])
    return _course_read(course, cover_map.get(course.id))


@router.patch("/courses/{course_id}/status", response_model=CourseRead)
def update_course_status(
    course_id: int,
    payload: CourseStatusUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = _require_course_in_tenant(db, tenant.id, course_id)
    _sync_course_publication_flag(course, _normalize_course_status(payload.status))
    db.add(course)
    db.commit()
    db.refresh(course)
    write_audit_log(
        db,
        action="courses.status",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course.id,
        details=course.status,
    )
    db.commit()
    cover_map = _course_cover_map(db, tenant.id, tenant.locale, [course])
    return _course_read(course, cover_map.get(course.id))


@router.post("/courses/{course_id}/publish", response_model=CourseRead)
def publish_course(
    course_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    return update_course_status(
        course_id,
        CourseStatusUpdate(status="published"),
        membership,
        tenant,
        db,
    )


@router.post("/courses/{course_id}/unpublish", response_model=CourseRead)
def unpublish_course(
    course_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    return update_course_status(
        course_id,
        CourseStatusUpdate(status="draft"),
        membership,
        tenant,
        db,
    )


@router.post("/courses/{course_id}/archive", response_model=CourseRead)
def archive_course(
    course_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    return update_course_status(
        course_id,
        CourseStatusUpdate(status="archived"),
        membership,
        tenant,
        db,
    )


@router.post("/courses/{course_id}/restore", response_model=CourseRead)
def restore_course(
    course_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseRead:
    return update_course_status(
        course_id,
        CourseStatusUpdate(status="draft"),
        membership,
        tenant,
        db,
    )


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    hard_delete: bool = False,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    course = _require_course_in_tenant(db, tenant.id, course_id)
    if not hard_delete:
        _sync_course_publication_flag(course, "archived")
        db.add(course)
        write_audit_log(
            db,
            action="courses.archive_via_delete",
            actor_user_id=membership.user_id,
            tenant_id=tenant.id,
            entity_type="course",
            entity_id=course.id,
            details=course.title,
        )
        db.commit()
        return {"deleted": False, "archived": True, "course_id": course.id, "impact": _course_dependency_impact(db, tenant.id, course.id)}
    deletion_summary = _delete_course_dependencies(db, tenant.id, course.id)
    db.execute(delete(Course).where(Course.tenant_id == tenant.id, Course.id == course.id))
    write_audit_log(
        db,
        action="courses.delete",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course.id,
        details=course.title,
    )
    db.commit()
    return {"deleted": True, "course_id": course.id, **deletion_summary}


@router.get("/courses/{course_id}/outline", response_model=CourseOutlineRead)
def get_course_outline(
    course_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> CourseOutlineRead:
    if membership.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return CourseOutlineRead.model_validate(build_course_outline(db, membership, course_id))


@router.get("/courses/{course_id}/sections", response_model=list[SectionRead])
def list_sections(
    course_id: int,
    _: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[SectionRead]:
    _require_course_in_tenant(db, tenant.id, course_id)
    sections = db.scalars(
        select(CourseSection)
        .where(CourseSection.tenant_id == tenant.id, CourseSection.course_id == course_id)
        .order_by(CourseSection.sort_order, CourseSection.id)
    ).all()
    return [_section_read(item) for item in sections]


@router.get("/courses/{course_id}/preview")
def preview_course_as_learner(
    course_id: int,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    course = _require_course_in_tenant(db, tenant.id, course_id)
    sections = db.scalars(
        select(CourseSection)
        .where(
            CourseSection.tenant_id == tenant.id,
            CourseSection.course_id == course_id,
            CourseSection.is_visible.is_(True),
        )
        .order_by(CourseSection.sort_order, CourseSection.id)
    ).all()
    lessons = db.scalars(
        select(Lesson)
        .where(
            Lesson.tenant_id == tenant.id,
            Lesson.course_id == course_id,
            Lesson.is_visible.is_(True),
            Lesson.is_published.is_(True),
        )
        .order_by(Lesson.section_id.is_(None), Lesson.section_id, Lesson.sort_order, Lesson.id)
    ).all()
    lesson_payload = [
        {
            "id": lesson.id,
            "section_id": lesson.section_id,
            "title": lesson.title,
            "summary": lesson.summary,
            "duration_minutes": lesson.duration_minutes,
        }
        for lesson in lessons
    ]
    return {
        "course": _course_read(course),
        "sections": [_section_read(section) for section in sections],
        "lessons": lesson_payload,
    }


@router.post("/courses/{course_id}/sections", response_model=SectionRead)
def create_section(
    course_id: int,
    payload: SectionCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> SectionRead:
    _require_course_in_tenant(db, tenant.id, course_id)
    section = CourseSection(
        tenant_id=tenant.id,
        course_id=course_id,
        title=payload.title,
        sort_order=payload.sort_order,
        is_visible=payload.is_visible,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    write_audit_log(
        db,
        action="sections.create",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="section",
        entity_id=section.id,
        details=section.title,
    )
    db.commit()
    return _section_read(section)


@router.patch("/courses/{course_id}/sections/{section_id}", response_model=SectionRead)
def update_section(
    course_id: int,
    section_id: int,
    payload: SectionUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> SectionRead:
    section = _require_section_in_course(db, tenant.id, course_id, section_id)
    section.title = payload.title
    section.sort_order = payload.sort_order
    section.is_visible = payload.is_visible
    db.add(section)
    db.commit()
    db.refresh(section)
    write_audit_log(
        db,
        action="sections.update",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="section",
        entity_id=section.id,
        details=section.title,
    )
    db.commit()
    return _section_read(section)


@router.post("/courses/{course_id}/sections/reorder")
def reorder_sections(
    course_id: int,
    payload: SectionReorderRequest,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    _require_course_in_tenant(db, tenant.id, course_id)
    sections = db.scalars(
        select(CourseSection).where(CourseSection.tenant_id == tenant.id, CourseSection.course_id == course_id)
    ).all()
    indexed = {item.id: item for item in sections}
    for index, section_id in enumerate(payload.section_ids):
        section = indexed.get(section_id)
        if section is None:
            continue
        section.sort_order = index + 1
        db.add(section)
    db.commit()
    write_audit_log(
        db,
        action="sections.reorder",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course_id,
    )
    db.commit()
    return {"updated": len(payload.section_ids)}


@router.delete("/courses/{course_id}/sections/{section_id}")
def delete_section(
    course_id: int,
    section_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    section = _require_section_in_course(db, tenant.id, course_id, section_id)
    db.execute(
        delete(CourseSection).where(
            CourseSection.id == section.id,
            CourseSection.course_id == course_id,
            CourseSection.tenant_id == tenant.id,
        )
    )
    for lesson in db.scalars(
        select(Lesson).where(Lesson.tenant_id == tenant.id, Lesson.course_id == course_id, Lesson.section_id == section.id)
    ).all():
        lesson.section_id = None
        db.add(lesson)
    db.commit()
    write_audit_log(
        db,
        action="sections.delete",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="section",
        entity_id=section.id,
        details=section.title,
    )
    db.commit()
    return {"deleted": True, "section_id": section.id}


@router.post("/courses/{course_id}/assign")
def assign_course(
    course_id: int,
    payload: AssignmentRequest,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    _require_course_in_tenant(db, tenant.id, course_id)
    if (payload.user_id is None and payload.group_id is None) or (payload.user_id is not None and payload.group_id is not None):
        raise HTTPException(status_code=422, detail="Provide exactly one of user_id or group_id")
    target_user_ids: set[int] = set()
    if payload.user_id is not None:
        _require_user_membership_in_tenant(db, tenant.id, payload.user_id)
        target_user_ids.add(payload.user_id)
    if payload.group_id is not None:
        group = db.scalar(select(Group.id).where(Group.id == payload.group_id, Group.tenant_id == tenant.id))
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        target_user_ids.update(
            db.scalars(
                select(GroupMember.user_id).where(
                    GroupMember.group_id == payload.group_id,
                    GroupMember.tenant_id == tenant.id,
                )
            ).all()
        )

    for user_id in target_user_ids:
        assignment_exists = db.scalar(
            select(CourseAssignment.id).where(
                CourseAssignment.tenant_id == tenant.id,
                CourseAssignment.course_id == course_id,
                CourseAssignment.user_id == user_id,
            )
        )
        if assignment_exists is None:
            db.add(
                CourseAssignment(
                    tenant_id=tenant.id,
                    course_id=course_id,
                    user_id=user_id,
                    group_id=payload.group_id,
                    assigned_by_id=membership.user_id,
                )
            )
        if db.scalar(select(Enrollment).where(Enrollment.tenant_id == tenant.id, Enrollment.course_id == course_id, Enrollment.user_id == user_id)) is None:
            db.add(Enrollment(tenant_id=tenant.id, course_id=course_id, user_id=user_id))
        send_mock_notification(db, tenant_id=tenant.id, user_id=user_id, payload={"type": "course_assigned", "course_id": course_id})
    write_audit_log(db, action="courses.assign", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="course", entity_id=course_id)
    db.commit()
    return {"assigned_users": len(target_user_ids)}


@router.get("/courses/{course_id}/assignments", response_model=list[CourseAssignmentRead])
def list_course_assignments(
    course_id: int,
    _: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[CourseAssignmentRead]:
    _require_course_in_tenant(db, tenant.id, course_id)
    rows = db.scalars(
        select(CourseAssignment)
        .where(
            CourseAssignment.tenant_id == tenant.id,
            CourseAssignment.course_id == course_id,
        )
        .order_by(CourseAssignment.created_at.desc(), CourseAssignment.id.desc())
    ).all()
    return [
        CourseAssignmentRead(
            id=row.id,
            user_id=row.user_id,
            group_id=row.group_id,
            assigned_by_id=row.assigned_by_id,
            created_at=row.created_at,
            effective_user_ids=_effective_user_ids_for_assignment(db, tenant.id, row),
        )
        for row in rows
    ]


@router.delete("/courses/{course_id}/assignments/{assignment_id}", status_code=204)
def delete_course_assignment(
    course_id: int,
    assignment_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> Response:
    _require_course_in_tenant(db, tenant.id, course_id)
    target = db.scalar(
        select(CourseAssignment).where(
            CourseAssignment.id == assignment_id,
            CourseAssignment.course_id == course_id,
            CourseAssignment.tenant_id == tenant.id,
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    target_user_ids = _effective_user_ids_for_assignment(db, tenant.id, target)
    db.delete(target)
    db.flush()
    for user_id in target_user_ids:
        if not _has_course_assignment_access(db, tenant.id, course_id, user_id):
            enrollment = db.scalar(
                select(Enrollment).where(
                    Enrollment.tenant_id == tenant.id,
                    Enrollment.course_id == course_id,
                    Enrollment.user_id == user_id,
                )
            )
            if enrollment is not None:
                db.delete(enrollment)
    write_audit_log(
        db,
        action="courses.assignment.delete",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course_assignment",
        entity_id=assignment_id,
    )
    db.commit()
    return Response(status_code=204)


@router.get("/courses/{course_id}/staff")
def list_course_staff(
    course_id: int,
    _: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    _require_course_in_tenant(db, tenant.id, course_id)
    rows = db.execute(
        select(CourseStaffAssignment, User)
        .join(User, User.id == CourseStaffAssignment.user_id)
        .where(CourseStaffAssignment.tenant_id == tenant.id, CourseStaffAssignment.course_id == course_id)
        .order_by(CourseStaffAssignment.role_name.asc(), User.full_name.asc(), User.id.asc())
    ).all()
    return [
        {
            "id": assignment.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role_name": assignment.role_name,
        }
        for assignment, user in rows
    ]


@router.post("/courses/{course_id}/staff")
def assign_course_staff(
    course_id: int,
    payload: StaffAssignmentRequest,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    _require_course_in_tenant(db, tenant.id, course_id)
    target_membership = db.scalar(
        select(Membership)
        .join(Role, Role.id == Membership.role_id)
        .where(
            Membership.tenant_id == tenant.id,
            Membership.user_id == payload.user_id,
            Membership.is_active.is_(True),
        )
    )
    if target_membership is None:
        raise HTTPException(status_code=422, detail="User must belong to the current tenant")
    if target_membership.role.name not in STAFF_ROLE_NAMES:
        raise HTTPException(status_code=422, detail="Only teacher or admin roles can be assigned as course staff")
    assignment = db.scalar(
        select(CourseStaffAssignment).where(
            CourseStaffAssignment.tenant_id == tenant.id,
            CourseStaffAssignment.course_id == course_id,
            CourseStaffAssignment.user_id == payload.user_id,
        )
    )
    if assignment is None:
        assignment = CourseStaffAssignment(
            tenant_id=tenant.id,
            course_id=course_id,
            user_id=payload.user_id,
            role_name=payload.role_name,
        )
    else:
        assignment.role_name = payload.role_name
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    write_audit_log(
        db,
        action="courses.staff.assign",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course_id,
        details=f"user_id={payload.user_id};role={payload.role_name}",
    )
    db.commit()
    return {"id": assignment.id, "user_id": assignment.user_id, "role_name": assignment.role_name}


@router.delete("/courses/{course_id}/staff/{user_id}")
def remove_course_staff(
    course_id: int,
    user_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    _require_course_in_tenant(db, tenant.id, course_id)
    assignment = db.scalar(
        select(CourseStaffAssignment).where(
            CourseStaffAssignment.tenant_id == tenant.id,
            CourseStaffAssignment.course_id == course_id,
            CourseStaffAssignment.user_id == user_id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Course staff assignment not found")
    db.execute(
        delete(CourseStaffAssignment).where(
            CourseStaffAssignment.tenant_id == tenant.id,
            CourseStaffAssignment.course_id == course_id,
            CourseStaffAssignment.user_id == user_id,
        )
    )
    db.commit()
    write_audit_log(
        db,
        action="courses.staff.remove",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="course",
        entity_id=course_id,
        details=f"user_id={user_id}",
    )
    db.commit()
    return {"deleted": True, "user_id": user_id}



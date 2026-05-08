from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.clock import utcnow
from app.core.db import get_db
from app.models.models import (
    Assignment,
    AssignmentSubmission,
    AssignmentSubmissionFile,
    Course,
    Enrollment,
    Lesson,
    Membership,
    RoleName,
    SubmissionReview,
    Tenant,
)
from app.schemas.assignment import (
    ASSIGNMENT_STATUSES,
    AssignmentCreate,
    AssignmentRead,
    AssignmentSubmissionRead,
    AssignmentUpdate,
    SubmissionFileRead,
    SubmissionReviewCreate,
    SubmissionReviewRead,
    SubmissionUpsert,
)
from app.services.notifications import send_mock_notification

router = APIRouter(tags=["assignments"])
STAFF_ROLES = (RoleName.org_admin, RoleName.teacher, RoleName.system_admin)
STAFF_ROLE_NAMES = {role.value for role in STAFF_ROLES}
UPLOAD_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _assignment_read(item: Assignment) -> AssignmentRead:
    return AssignmentRead.model_validate(item)


def _submission_read(db: Session, submission: AssignmentSubmission) -> AssignmentSubmissionRead:
    files = db.scalars(
        select(AssignmentSubmissionFile).where(
            AssignmentSubmissionFile.tenant_id == submission.tenant_id,
            AssignmentSubmissionFile.submission_id == submission.id,
        )
    ).all()
    latest_review = db.scalar(
        select(SubmissionReview)
        .where(
            SubmissionReview.tenant_id == submission.tenant_id,
            SubmissionReview.submission_id == submission.id,
        )
        .order_by(SubmissionReview.created_at.desc(), SubmissionReview.id.desc())
    )
    return AssignmentSubmissionRead(
        id=submission.id,
        assignment_id=submission.assignment_id,
        student_user_id=submission.student_user_id,
        status=submission.status,
        text_answer=submission.text_answer,
        link_answer=submission.link_answer,
        submitted_at=submission.submitted_at,
        updated_at=submission.updated_at,
        files=[SubmissionFileRead.model_validate(item) for item in files],
        latest_review=SubmissionReviewRead.model_validate(latest_review) if latest_review else None,
    )


def _require_assignment(db: Session, tenant_id: int, assignment_id: int) -> Assignment:
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.tenant_id == tenant_id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _ensure_course_and_lesson_in_tenant(
    db: Session, tenant_id: int, course_id: int, lesson_id: int | None
) -> None:
    course = db.scalar(select(Course.id).where(Course.id == course_id, Course.tenant_id == tenant_id))
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if lesson_id is None:
        return
    lesson = db.scalar(
        select(Lesson.id).where(
            Lesson.id == lesson_id,
            Lesson.tenant_id == tenant_id,
            Lesson.course_id == course_id,
        )
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")


def _normalize_page_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported assignment status")
    return normalized


def _ensure_learner_has_course_access(db: Session, tenant_id: int, user_id: int, course_id: int) -> None:
    enrollment = db.scalar(
        select(Enrollment.id).where(
            Enrollment.tenant_id == tenant_id,
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=403, detail="Course is not assigned to this learner")


def _tenant_media_root(tenant_code: str) -> Path:
    sanitized = "".join(ch.lower() if ch.isalnum() or ch == "-" else "-" for ch in tenant_code).strip("-") or "tenant"
    media_root = Path(__file__).resolve().parents[2] / "static" / "media" / sanitized
    media_root.mkdir(parents=True, exist_ok=True)
    return media_root


def _normalize_upload_filename(source_name: str) -> str:
    safe_name = Path(source_name or "").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        allowed = ", ".join(sorted(UPLOAD_SUFFIXES))
        raise HTTPException(status_code=422, detail=f"Unsupported file format. Allowed: {allowed}")
    stem = "".join(ch.lower() if ch.isalnum() else "-" for ch in Path(safe_name).stem).strip("-") or "submission"
    return f"submission-{stem}-{uuid4().hex[:12]}{suffix}"


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(
    course_id: int | None = None,
    lesson_id: int | None = None,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    query = select(Assignment).where(Assignment.tenant_id == tenant.id)
    if course_id is not None:
        query = query.where(Assignment.course_id == course_id)
    if lesson_id is not None:
        query = query.where(Assignment.lesson_id == lesson_id)
    assignments = db.scalars(query.order_by(Assignment.created_at.desc(), Assignment.id.desc())).all()
    if membership.role.name in STAFF_ROLE_NAMES:
        return [_assignment_read(item) for item in assignments]

    allowed_course_ids = {
        item
        for item in db.scalars(
            select(Enrollment.course_id).where(
                Enrollment.tenant_id == tenant.id,
                Enrollment.user_id == membership.user_id,
            )
        ).all()
    }
    visible = [item for item in assignments if item.course_id in allowed_course_ids and item.is_active]
    return [_assignment_read(item) for item in visible]


@router.post("/assignments", response_model=AssignmentRead)
def create_assignment(
    payload: AssignmentCreate,
    membership: Membership = Depends(require_roles(*STAFF_ROLES)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> AssignmentRead:
    _ensure_course_and_lesson_in_tenant(db, tenant.id, payload.course_id, payload.lesson_id)
    assignment = Assignment(
        tenant_id=tenant.id,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        page_id=_normalize_page_id(payload.page_id),
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
        due_at=payload.due_at,
        created_by_id=membership.user_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    write_audit_log(
        db,
        action="assignments.create",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="assignment",
        entity_id=assignment.id,
        details=assignment.title,
    )
    db.commit()
    return _assignment_read(assignment)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    membership: Membership = Depends(require_roles(*STAFF_ROLES)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> AssignmentRead:
    assignment = _require_assignment(db, tenant.id, assignment_id)
    assignment.title = payload.title
    assignment.description = payload.description
    assignment.is_active = payload.is_active
    assignment.due_at = payload.due_at
    assignment.page_id = _normalize_page_id(payload.page_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    write_audit_log(
        db,
        action="assignments.update",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="assignment",
        entity_id=assignment.id,
        details=assignment.title,
    )
    db.commit()
    return _assignment_read(assignment)


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    membership: Membership = Depends(require_roles(*STAFF_ROLES)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    assignment = _require_assignment(db, tenant.id, assignment_id)
    submission_ids = db.scalars(
        select(AssignmentSubmission.id).where(
            AssignmentSubmission.tenant_id == tenant.id,
            AssignmentSubmission.assignment_id == assignment.id,
        )
    ).all()
    if submission_ids:
        db.execute(
            delete(AssignmentSubmissionFile).where(
                AssignmentSubmissionFile.tenant_id == tenant.id,
                AssignmentSubmissionFile.submission_id.in_(submission_ids),
            )
        )
        db.execute(
            delete(SubmissionReview).where(
                SubmissionReview.tenant_id == tenant.id,
                SubmissionReview.submission_id.in_(submission_ids),
            )
        )
        db.execute(
            delete(AssignmentSubmission).where(
                AssignmentSubmission.tenant_id == tenant.id,
                AssignmentSubmission.id.in_(submission_ids),
            )
        )
    db.delete(assignment)
    db.commit()
    write_audit_log(
        db,
        action="assignments.delete",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="assignment",
        entity_id=assignment_id,
        details=assignment.title,
    )
    db.commit()
    return {"deleted": assignment_id}


@router.get("/assignments/{assignment_id}/submissions", response_model=list[AssignmentSubmissionRead])
def list_assignment_submissions(
    assignment_id: int,
    status: str | None = None,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[AssignmentSubmissionRead]:
    assignment = _require_assignment(db, tenant.id, assignment_id)
    query = select(AssignmentSubmission).where(
        AssignmentSubmission.tenant_id == tenant.id,
        AssignmentSubmission.assignment_id == assignment.id,
    )
    if status:
        query = query.where(AssignmentSubmission.status == _validate_status(status))
    if membership.role.name not in STAFF_ROLE_NAMES:
        _ensure_learner_has_course_access(db, tenant.id, membership.user_id, assignment.course_id)
        query = query.where(AssignmentSubmission.student_user_id == membership.user_id)
    submissions = db.scalars(query.order_by(AssignmentSubmission.updated_at.desc(), AssignmentSubmission.id.desc())).all()
    return [_submission_read(db, item) for item in submissions]


@router.post("/assignments/{assignment_id}/submissions", response_model=AssignmentSubmissionRead)
def upsert_submission(
    assignment_id: int,
    payload: SubmissionUpsert,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> AssignmentSubmissionRead:
    assignment = _require_assignment(db, tenant.id, assignment_id)
    _ensure_learner_has_course_access(db, tenant.id, membership.user_id, assignment.course_id)
    status = _validate_status(payload.status)
    if membership.role.name in STAFF_ROLE_NAMES and status in {"submitted", "approved", "in_review", "needs_revision", "rejected"}:
        raise HTTPException(status_code=403, detail="Staff cannot submit learner work")

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.tenant_id == tenant.id,
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_user_id == membership.user_id,
        )
    )
    if submission is None:
        submission = AssignmentSubmission(
            tenant_id=tenant.id,
            assignment_id=assignment.id,
            student_user_id=membership.user_id,
        )
    submission.text_answer = payload.text_answer
    submission.link_answer = payload.link_answer
    submission.status = status
    submission.updated_at = utcnow()
    if status == "submitted":
        submission.submitted_at = utcnow()

    db.add(submission)
    db.flush()
    db.execute(
        delete(AssignmentSubmissionFile).where(
            AssignmentSubmissionFile.tenant_id == tenant.id,
            AssignmentSubmissionFile.submission_id == submission.id,
        )
    )
    for file_url in payload.file_urls:
        normalized = file_url.strip()
        if not normalized:
            continue
        db.add(
            AssignmentSubmissionFile(
                tenant_id=tenant.id,
                submission_id=submission.id,
                file_url=normalized,
                file_name=normalized.split("/")[-1],
            )
        )
    db.commit()
    db.refresh(submission)

    if status == "submitted":
        send_mock_notification(
            db,
            tenant_id=tenant.id,
            user_id=assignment.created_by_id,
            payload={
                "type": "assignment_submitted",
                "assignment_id": assignment.id,
                "submission_id": submission.id,
                "student_user_id": membership.user_id,
            },
        )
        db.commit()

    write_audit_log(
        db,
        action="assignment_submissions.upsert",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="assignment_submission",
        entity_id=submission.id,
        details=submission.status,
    )
    db.commit()
    return _submission_read(db, submission)


@router.post("/assignments/submissions/upload")
async def upload_submission_file(
    assignment_id: int = Form(...),
    file: UploadFile = File(...),
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    assignment = _require_assignment(db, tenant.id, assignment_id)
    _ensure_learner_has_course_access(db, tenant.id, membership.user_id, assignment.course_id)
    if not file.filename:
        raise HTTPException(status_code=422, detail="File name is required")
    filename = _normalize_upload_filename(file.filename)
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    media_root = _tenant_media_root(tenant.code)
    destination = media_root / filename
    destination.write_bytes(payload)
    return {"file_url": f"/media/{media_root.name}/{filename}", "file_name": file.filename}


@router.post("/submissions/{submission_id}/review", response_model=AssignmentSubmissionRead)
def review_submission(
    submission_id: int,
    payload: SubmissionReviewCreate,
    membership: Membership = Depends(require_roles(*STAFF_ROLES)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> AssignmentSubmissionRead:
    review_status = _validate_status(payload.status)
    if review_status not in {"in_review", "approved", "needs_revision", "rejected"}:
        raise HTTPException(status_code=422, detail="Review endpoint accepts review statuses only")

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.tenant_id == tenant.id,
        )
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    assignment = _require_assignment(db, tenant.id, submission.assignment_id)
    _ensure_course_and_lesson_in_tenant(db, tenant.id, assignment.course_id, assignment.lesson_id)

    submission.status = review_status
    submission.updated_at = utcnow()
    review = SubmissionReview(
        tenant_id=tenant.id,
        submission_id=submission.id,
        reviewer_user_id=membership.user_id,
        status=review_status,
        comment=payload.comment,
        grade=payload.grade,
    )
    db.add(submission)
    db.add(review)
    db.commit()
    db.refresh(submission)

    send_mock_notification(
        db,
        tenant_id=tenant.id,
        user_id=submission.student_user_id,
        payload={
            "type": "assignment_reviewed",
            "assignment_id": assignment.id,
            "submission_id": submission.id,
            "status": review_status,
        },
    )
    write_audit_log(
        db,
        action="assignment_submissions.review",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="assignment_submission",
        entity_id=submission.id,
        details=review_status,
    )
    db.commit()
    return _submission_read(db, submission)

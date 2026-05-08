from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, require_roles, tenant_context
from app.core.db import get_db
from app.models.models import Course, CourseRecommendation, EditorRecommendation, Lesson, Membership, Recommendation, RoleName, Tenant
from app.schemas.recommendation import (
    EditorRecommendationCreate,
    EditorRecommendationRead,
    EditorRecommendationUpdate,
)
from app.services.recommendation_payloads import (
    latest_unique_recommendations,
    serialize_recommendations,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/me")
def my_recommendations(membership: Membership = Depends(active_membership), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> list[dict]:
    items = db.scalars(select(Recommendation).where(Recommendation.tenant_id == tenant.id, Recommendation.user_id == membership.user_id).order_by(Recommendation.priority)).all()
    return serialize_recommendations(
        db,
        latest_unique_recommendations(items),
        tenant.locale,
    )


@router.get("/editor", response_model=list[EditorRecommendationRead])
def list_editor_recommendations(
    course_id: int | None = None,
    lesson_id: int | None = None,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[EditorRecommendationRead]:
    query = select(EditorRecommendation).where(EditorRecommendation.tenant_id == tenant.id)
    if course_id is not None:
        query = query.join(
            CourseRecommendation,
            (CourseRecommendation.recommendation_id == EditorRecommendation.id)
            & (CourseRecommendation.tenant_id == tenant.id),
        ).where(CourseRecommendation.course_id == course_id)
    if lesson_id is not None:
        query = query.where(EditorRecommendation.lesson_id == lesson_id)
    items = db.scalars(query.order_by(EditorRecommendation.sort_order, EditorRecommendation.id)).all()
    return [EditorRecommendationRead.model_validate(item) for item in items]


def _validate_course_lesson_scope(db: Session, tenant_id: int, course_id: int | None, lesson_id: int | None) -> None:
    if course_id is not None:
        course_exists = db.scalar(select(Course.id).where(Course.id == course_id, Course.tenant_id == tenant_id))
        if course_exists is None:
            raise HTTPException(status_code=404, detail="Course not found")
    if lesson_id is not None:
        lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant_id))
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
        if course_id is not None and lesson.course_id != course_id:
            raise HTTPException(status_code=422, detail="Lesson does not belong to selected course")


@router.post("/editor", response_model=EditorRecommendationRead)
def create_editor_recommendation(
    payload: EditorRecommendationCreate,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> EditorRecommendationRead:
    _validate_course_lesson_scope(db, tenant.id, payload.course_id, payload.lesson_id)
    item = EditorRecommendation(
        tenant_id=tenant.id,
        title=payload.title,
        text=payload.text,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(item)
    db.flush()
    if payload.course_id is not None:
        db.add(
            CourseRecommendation(
                tenant_id=tenant.id,
                course_id=payload.course_id,
                recommendation_id=item.id,
            )
        )
    db.commit()
    db.refresh(item)
    return EditorRecommendationRead.model_validate(item)


@router.patch("/editor/{recommendation_id}", response_model=EditorRecommendationRead)
def update_editor_recommendation(
    recommendation_id: int,
    payload: EditorRecommendationUpdate,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> EditorRecommendationRead:
    item = db.scalar(
        select(EditorRecommendation).where(
            EditorRecommendation.id == recommendation_id,
            EditorRecommendation.tenant_id == tenant.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _validate_course_lesson_scope(db, tenant.id, payload.course_id, payload.lesson_id)
    item.title = payload.title
    item.text = payload.text
    item.course_id = payload.course_id
    item.lesson_id = payload.lesson_id
    item.sort_order = payload.sort_order
    item.is_active = payload.is_active
    db.add(item)
    db.execute(
        delete(CourseRecommendation).where(
            CourseRecommendation.tenant_id == tenant.id,
            CourseRecommendation.recommendation_id == item.id,
        )
    )
    if payload.course_id is not None:
        db.add(
            CourseRecommendation(
                tenant_id=tenant.id,
                course_id=payload.course_id,
                recommendation_id=item.id,
            )
        )
    db.commit()
    db.refresh(item)
    return EditorRecommendationRead.model_validate(item)


@router.delete("/editor/{recommendation_id}")
def delete_editor_recommendation(
    recommendation_id: int,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    item = db.scalar(
        select(EditorRecommendation).where(
            EditorRecommendation.id == recommendation_id,
            EditorRecommendation.tenant_id == tenant.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    db.execute(
        delete(CourseRecommendation).where(
            CourseRecommendation.tenant_id == tenant.id,
            CourseRecommendation.recommendation_id == recommendation_id,
        )
    )
    db.delete(item)
    db.commit()
    return {"deleted": True, "recommendation_id": recommendation_id}

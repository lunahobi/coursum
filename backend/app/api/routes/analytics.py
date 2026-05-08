from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles, tenant_context
from app.core.db import get_db
from app.models.models import Membership, RoleName, Tenant
from app.services.analytics import activity_timeline, course_progress, dashboard_stats, learner_report, problem_topics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(
    course_id: list[int] | None = Query(default=None),
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    return dashboard_stats(db, tenant.id, course_id)


@router.get("/course-progress")
def analytics_course_progress(
    course_id: list[int] | None = Query(default=None),
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    return course_progress(db, tenant.id, course_id)


@router.get("/problem-topics")
def analytics_problem_topics(
    course_id: list[int] | None = Query(default=None),
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    return problem_topics(db, tenant.id, course_id)


@router.get("/timeline")
def analytics_timeline(
    period: str = Query(default="30d", pattern="^(7d|30d|quarter|all)$"),
    course_id: list[int] | None = Query(default=None),
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    return activity_timeline(db, tenant.id, period, course_id)


@router.get("/learners/{user_id}")
def analytics_learner(user_id: int, _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> dict:
    return learner_report(db, tenant.id, user_id, tenant.locale)

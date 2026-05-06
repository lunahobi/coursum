from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import Attempt, Course, Enrollment, Membership, Recommendation, Result, Test, Topic
from app.services.recommendation_payloads import (
    latest_unique_recommendations,
    serialize_recommendations,
)


def dashboard_stats(db: Session, tenant_id: int) -> dict:
    avg_progress = db.scalar(
        select(func.avg(Enrollment.progress_percent)).where(Enrollment.tenant_id == tenant_id)
    )
    return {
        "users": db.scalar(select(func.count(Membership.id)).where(Membership.tenant_id == tenant_id, Membership.is_active.is_(True))) or 0,
        "courses": db.scalar(select(func.count(Course.id)).where(Course.tenant_id == tenant_id)) or 0,
        "tests": db.scalar(select(func.count(Test.id)).where(Test.tenant_id == tenant_id)) or 0,
        "active_attempts": db.scalar(select(func.count(Attempt.id)).where(Attempt.tenant_id == tenant_id, Attempt.status == "in_progress")) or 0,
        "enrollments": db.scalar(select(func.count(Enrollment.id)).where(Enrollment.tenant_id == tenant_id)) or 0,
        "avg_progress": int(avg_progress or 0),
        "recommendations": db.scalar(select(func.count(Recommendation.id)).where(Recommendation.tenant_id == tenant_id)) or 0,
    }


def course_progress(db: Session, tenant_id: int) -> list[dict]:
    rows = db.execute(
        select(Course.title, func.avg(Enrollment.progress_percent), func.count(Enrollment.id))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.tenant_id == tenant_id)
        .group_by(Course.title)
    ).all()
    return [{"course_title": title, "avg_progress": int(avg_progress or 0), "learners": learners} for title, avg_progress, learners in rows]


def problem_topics(db: Session, tenant_id: int) -> list[dict]:
    rows = db.execute(
        select(Topic.title, func.count(Recommendation.id))
        .join(Recommendation, Recommendation.topic_id == Topic.id)
        .where(Topic.tenant_id == tenant_id, Recommendation.tenant_id == tenant_id)
        .group_by(Topic.id, Topic.title)
        .order_by(func.count(Recommendation.id).desc(), Topic.title.asc())
    ).all()
    return [{"topic_title": title, "recommendations": count} for title, count in rows]


def learner_report(db: Session, tenant_id: int, user_id: int, tenant_locale: str | None) -> dict:
    results = db.scalars(select(Result).join(Attempt, Attempt.id == Result.attempt_id).where(Attempt.tenant_id == tenant_id, Attempt.user_id == user_id)).all()
    recommendations = db.scalars(select(Recommendation).where(Recommendation.tenant_id == tenant_id, Recommendation.user_id == user_id)).all()
    return {
        "results": [{"score_percent": item.score_percent, "weak_topics": item.weak_topics} for item in results],
        "recommendations": serialize_recommendations(
            db,
            latest_unique_recommendations(recommendations),
            tenant_locale,
        ),
    }

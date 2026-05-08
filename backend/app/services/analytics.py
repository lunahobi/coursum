from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import Attempt, Course, Enrollment, Lesson, Membership, Recommendation, Result, Test, Topic
from app.services.recommendation_payloads import (
    latest_unique_recommendations,
    serialize_recommendations,
)


def dashboard_stats(db: Session, tenant_id: int, course_ids: list[int] | None = None) -> dict:
    selected_course_ids = [int(course_id) for course_id in (course_ids or [])]
    has_filter = bool(selected_course_ids)
    enrollment_filters = [Enrollment.tenant_id == tenant_id]
    test_filters = [Test.tenant_id == tenant_id]
    attempt_filters = [Attempt.tenant_id == tenant_id, Attempt.status == "in_progress"]
    course_filters = [Course.tenant_id == tenant_id]
    if has_filter:
        enrollment_filters.append(Enrollment.course_id.in_(selected_course_ids))
        test_filters.append(Test.course_id.in_(selected_course_ids))
        course_filters.append(Course.id.in_(selected_course_ids))
    avg_progress = db.scalar(select(func.avg(Enrollment.progress_percent)).where(*enrollment_filters))
    active_learners = (
        db.scalar(select(func.count(func.distinct(Enrollment.user_id))).where(*enrollment_filters))
        if has_filter
        else db.scalar(select(func.count(Membership.id)).where(Membership.tenant_id == tenant_id, Membership.is_active.is_(True)))
    )
    return {
        "users": active_learners or 0,
        "courses": db.scalar(select(func.count(Course.id)).where(*course_filters)) or 0,
        "tests": db.scalar(select(func.count(Test.id)).where(*test_filters)) or 0,
        "active_attempts": (
            db.scalar(
                select(func.count(Attempt.id))
                .join(Test, Test.id == Attempt.test_id)
                .where(*attempt_filters, *( [Test.course_id.in_(selected_course_ids)] if has_filter else [] ))
            )
            or 0
        ),
        "enrollments": db.scalar(select(func.count(Enrollment.id)).where(*enrollment_filters)) or 0,
        "avg_progress": int(avg_progress or 0),
        "recommendations": (
            db.scalar(
                select(func.count(Recommendation.id))
                .join(Result, Result.id == Recommendation.result_id)
                .join(Attempt, Attempt.id == Result.attempt_id)
                .join(Test, Test.id == Attempt.test_id)
                .where(
                    Recommendation.tenant_id == tenant_id,
                    *( [Test.course_id.in_(selected_course_ids)] if has_filter else [] ),
                )
            )
            or 0
        ),
    }


def course_progress(db: Session, tenant_id: int, course_ids: list[int] | None = None) -> list[dict]:
    selected_course_ids = [int(course_id) for course_id in (course_ids or [])]
    query = (
        select(Course.id, Course.title, func.avg(Enrollment.progress_percent), func.count(Enrollment.id))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.tenant_id == tenant_id)
    )
    if selected_course_ids:
        query = query.where(Course.id.in_(selected_course_ids))
    rows = db.execute(query.group_by(Course.id, Course.title)).all()
    return [{"course_id": course_id, "course_title": title, "avg_progress": int(avg_progress or 0), "learners": learners} for course_id, title, avg_progress, learners in rows]


def problem_topics(db: Session, tenant_id: int, course_ids: list[int] | None = None) -> list[dict]:
    selected_course_ids = [int(course_id) for course_id in (course_ids or [])]
    topic_query = (
        select(Recommendation.topic_id, func.count(Recommendation.id))
        .join(Result, Result.id == Recommendation.result_id)
        .join(Attempt, Attempt.id == Result.attempt_id)
        .join(Test, Test.id == Attempt.test_id)
        .where(Recommendation.tenant_id == tenant_id, Recommendation.topic_id.is_not(None))
    )
    if selected_course_ids:
        topic_query = topic_query.where(Test.course_id.in_(selected_course_ids))
    rows = db.execute(topic_query.group_by(Recommendation.topic_id)).all()
    if not rows:
        return []
    topic_counts = {int(topic_id): count for topic_id, count in rows if topic_id is not None}
    topic_ids = list(topic_counts.keys())
    lesson_title_by_topic = {
        topic_id: title
        for topic_id, title in db.execute(
            select(Lesson.topic_id, Lesson.title)
            .where(
                Lesson.tenant_id == tenant_id,
                Lesson.topic_id.in_(topic_ids),
            )
            .order_by(Lesson.sort_order, Lesson.id)
        ).all()
        if topic_id is not None
    }
    topic_title_by_id = {
        topic_id: title
        for topic_id, title in db.execute(
            select(Topic.id, Topic.title).where(Topic.tenant_id == tenant_id, Topic.id.in_(topic_ids))
        ).all()
    }
    payload = []
    for topic_id, count in topic_counts.items():
        payload.append(
            {
                "topic_title": lesson_title_by_topic.get(topic_id) or topic_title_by_id.get(topic_id, str(topic_id)),
                "recommendations": count,
            }
        )
    payload.sort(key=lambda item: (-item["recommendations"], item["topic_title"]))
    return payload


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

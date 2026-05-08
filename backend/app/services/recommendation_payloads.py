from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.content_localization import recommendation_reason
from app.models.models import Course, Lesson, Recommendation, Result, Topic


def _weak_topic_score(result: Result | None, topic_id: int | None) -> int:
    if result is None or topic_id is None:
        return 0
    for item in result.weak_topics or []:
        if item.get("topic_id") == topic_id:
            return int(item.get("score") or 0)
    return 0


def _resolve_context(
    db: Session, recommendation: Recommendation
) -> tuple[Topic | None, Lesson | None, Course | None]:
    topic = db.get(Topic, recommendation.topic_id) if recommendation.topic_id else None
    lesson = db.get(Lesson, recommendation.lesson_id) if recommendation.lesson_id else None
    course = db.get(Course, lesson.course_id) if lesson else None

    if lesson is None and recommendation.topic_id is not None:
        row = db.execute(
            select(Lesson, Course)
            .join(Course, Course.id == Lesson.course_id)
            .where(
                Lesson.tenant_id == recommendation.tenant_id,
                Lesson.topic_id == recommendation.topic_id,
            )
            .order_by(Lesson.sort_order, Lesson.id)
        ).first()
        if row is not None:
            lesson, course = row

    return topic, lesson, course


def serialize_recommendation(
    db: Session, recommendation: Recommendation, tenant_locale: str | None
) -> dict:
    result = db.get(Result, recommendation.result_id) if recommendation.result_id else None
    topic, lesson, course = _resolve_context(db, recommendation)
    signal_score = _weak_topic_score(result, recommendation.topic_id)
    signal_level = "high" if signal_score >= 4 else "medium" if signal_score >= 2 else "low"
    topic_title = lesson.title if lesson else (topic.title if topic else None)

    return {
        "id": recommendation.id,
        "priority": recommendation.priority,
        "text": recommendation.text,
        "topic_id": recommendation.topic_id,
        "topic_title": topic_title,
        "lesson_id": lesson.id if lesson else recommendation.lesson_id,
        "lesson_title": lesson.title if lesson else None,
        "course_id": course.id if course else None,
        "course_title": course.title if course else None,
        "signal_score": signal_score,
        "signal_level": signal_level,
        "reason": recommendation_reason(tenant_locale, topic_title, signal_score),
    }


def serialize_recommendations(
    db: Session, recommendations: list[Recommendation], tenant_locale: str | None
) -> list[dict]:
    return [
        serialize_recommendation(db, recommendation, tenant_locale)
        for recommendation in recommendations
    ]


def latest_unique_recommendations(
    recommendations: list[Recommendation],
) -> list[Recommendation]:
    unique_items: dict[str, Recommendation] = {}
    for recommendation in sorted(recommendations, key=lambda item: item.id, reverse=True):
        key = (
            f"topic:{recommendation.topic_id}"
            if recommendation.topic_id is not None
            else f"text:{recommendation.text}"
        )
        unique_items.setdefault(key, recommendation)
    return sorted(
        unique_items.values(),
        key=lambda item: (item.priority, -item.id),
    )

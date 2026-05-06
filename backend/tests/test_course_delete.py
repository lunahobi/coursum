from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import (
    AnswerOption,
    Attempt,
    AttemptAnswer,
    Course,
    CourseAssignment,
    Enrollment,
    Lesson,
    LessonProgress,
    Question,
    Recommendation,
    Result,
    Test,
)

from .conftest import auth_headers


def test_teacher_can_hard_delete_course_with_related_lessons_and_tests(client):
    db = SessionLocal()
    try:
        correct_option = db.scalar(select(AnswerOption).where(AnswerOption.question_id == 1, AnswerOption.is_correct.is_(True)))
        attempt = Attempt(
            tenant_id=1,
            test_id=1,
            user_id=3,
            current_difficulty=3,
            status="completed",
            asked_question_ids=[1],
            difficulty_path=[3],
        )
        db.add(attempt)
        db.flush()
        db.add(CourseAssignment(tenant_id=1, course_id=1, user_id=3, assigned_by_id=2))
        db.add(
            LessonProgress(
                tenant_id=1,
                user_id=3,
                course_id=1,
                lesson_id=1,
                current_page_index=1,
                completed_page_ids=["passwords-overview"],
                is_completed=False,
                last_video_position_seconds=42,
            )
        )
        db.add(
            AttemptAnswer(
                tenant_id=1,
                attempt_id=attempt.id,
                question_id=1,
                answer_option_id=correct_option.id if correct_option else None,
                is_correct=True,
                response_seconds=12,
            )
        )
        result = Result(tenant_id=1, attempt_id=attempt.id, score_percent=100, weak_topics=[], recommendation_count=1)
        db.add(result)
        db.flush()
        db.add(Recommendation(tenant_id=1, user_id=3, result_id=result.id, topic_id=1, lesson_id=1, priority=1, text="Repeat the lesson"))
        db.commit()
    finally:
        db.close()

    response = client.delete("/api/v1/courses/1?hard_delete=true", headers=auth_headers(client, "teacher-a@example.com", "tenant-a"))

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert response.json()["course_id"] == 1
    assert response.json()["deleted_lessons"] == 2
    assert response.json()["deleted_tests"] == 1

    db = SessionLocal()
    try:
        assert db.get(Course, 1) is None
        assert db.scalar(select(Lesson).where(Lesson.course_id == 1)) is None
        assert db.scalar(select(LessonProgress).where(LessonProgress.course_id == 1)) is None
        assert db.scalar(select(Enrollment).where(Enrollment.course_id == 1)) is None
        assert db.scalar(select(CourseAssignment).where(CourseAssignment.course_id == 1)) is None
        assert db.scalar(select(Test).where(Test.course_id == 1)) is None
        assert db.scalar(select(Question).where(Question.test_id == 1)) is None
        assert db.scalar(select(Attempt).where(Attempt.test_id == 1)) is None
        assert db.scalar(select(AttemptAnswer)) is None
        assert db.scalar(select(Result)) is None
        assert db.scalar(select(Recommendation)) is None
    finally:
        db.close()


def test_delete_course_archives_by_default(client):
    response = client.delete("/api/v1/courses/1", headers=auth_headers(client, "teacher-a@example.com", "tenant-a"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted"] is False
    assert payload["archived"] is True
    assert payload["course_id"] == 1

    db = SessionLocal()
    try:
        course = db.get(Course, 1)
        assert course is not None
        assert course.status == "archived"
        assert course.is_published is False
    finally:
        db.close()

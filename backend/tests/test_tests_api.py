from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import AnswerOption, Attempt, AttemptAnswer, Question, Test

from .conftest import auth_headers


def test_teacher_can_update_and_delete_test(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    updated = client.patch(
        "/api/v1/tests/1",
        headers=headers,
        json={"title": "Updated password test", "baseline_difficulty": 4, "question_limit": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["baseline_difficulty"] == 4
    assert updated.json()["question_limit"] == 3

    deleted = client.delete("/api/v1/tests/1", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    listed = client.get("/api/v1/tests", headers=headers).json()
    assert all(item["id"] != 1 for item in listed)

    db = SessionLocal()
    try:
        assert db.get(Test, 1) is None
    finally:
        db.close()


def test_teacher_can_switch_active_test_for_course(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    created = client.post(
        "/api/v1/tests",
        headers=headers,
        json={
            "course_id": 1,
            "title": "Second test",
            "baseline_difficulty": 3,
            "question_limit": 5,
        },
    )
    assert created.status_code == 200
    second_test_id = created.json()["id"]

    listed_before = client.get("/api/v1/tests", headers=headers)
    assert listed_before.status_code == 200
    before_items = [item for item in listed_before.json() if item["course_id"] == 1]
    assert any(item["id"] == 1 and item["is_active"] for item in before_items)
    assert any(item["id"] == second_test_id and not item["is_active"] for item in before_items)

    activated = client.post(f"/api/v1/tests/{second_test_id}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    listed_after = client.get("/api/v1/tests", headers=headers)
    assert listed_after.status_code == 200
    after_items = [item for item in listed_after.json() if item["course_id"] == 1]
    assert any(item["id"] == second_test_id and item["is_active"] for item in after_items)
    assert any(item["id"] == 1 and not item["is_active"] for item in after_items)


def test_teacher_can_delete_question(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    response = client.delete("/api/v1/questions/1", headers=headers)
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    listed = client.get("/api/v1/questions?test_id=1", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert all(item["id"] != 1 for item in payload)

    db = SessionLocal()
    try:
        assert db.get(Question, 1) is None
    finally:
        db.close()


def test_teacher_cannot_delete_question_used_in_attempt(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    db = SessionLocal()
    try:
        correct_option = db.scalar(select(AnswerOption).where(AnswerOption.question_id == 1, AnswerOption.is_correct.is_(True)))
        attempt = Attempt(
            tenant_id=1,
            test_id=1,
            user_id=4,
            current_difficulty=3,
            status="in_progress",
            asked_question_ids=[1],
            difficulty_path=[3],
        )
        db.add(attempt)
        db.flush()

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
        db.commit()
    finally:
        db.close()

    response = client.delete("/api/v1/questions/1", headers=headers)
    assert response.status_code == 409


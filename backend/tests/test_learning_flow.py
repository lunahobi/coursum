from app.api.routes.tests import _ordered_options
from app.core.db import SessionLocal
from app.models.models import AnswerOption, Attempt, Question, Recommendation, Result

from .conftest import auth_headers


def test_learner_can_complete_test_and_get_recommendations(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    start = client.post("/api/v1/tests/1/start", headers=headers)
    attempt_id = start.json()["attempt_id"]
    assert start.json()["question_limit"] == 2
    next_question = client.get(f"/api/v1/attempts/{attempt_id}/next-question", headers=headers).json()
    assert next_question["question_number"] == 1
    assert next_question["total_questions"] == 2
    submit = client.post(
        f"/api/v1/attempts/{attempt_id}/submit-answer",
        headers=headers,
        json={
            "question_id": next_question["id"],
            "answer_option_id": None,
            "response_seconds": 45,
        },
    )
    assert submit.status_code == 200
    assert submit.json()["current_difficulty"] == 2
    assert submit.json()["remaining_questions"] == 1
    second_question = client.get(
        f"/api/v1/attempts/{attempt_id}/next-question", headers=headers
    ).json()
    assert second_question["question_number"] == 2
    db = SessionLocal()
    try:
        second_answer_id = (
            db.query(AnswerOption)
            .filter(
                AnswerOption.question_id == second_question["id"],
                AnswerOption.is_correct.is_(True),
            )
            .first()
            .id
        )
    finally:
        db.close()
    second_submit = client.post(
        f"/api/v1/attempts/{attempt_id}/submit-answer",
        headers=headers,
        json={
            "question_id": second_question["id"],
            "answer_option_id": second_answer_id,
            "response_seconds": 18,
        },
    )
    assert second_submit.status_code == 200
    assert second_submit.json()["remaining_questions"] == 0
    finish = client.post(f"/api/v1/attempts/{attempt_id}/finish", headers=headers)
    assert finish.status_code == 200
    assert finish.json()["recommendation_count"] >= 1
    assert finish.json()["total_questions"] == 2
    assert len(finish.json()["difficulty_path"]) == 3
    assert finish.json()["correct_answers"] == 1
    assert len(finish.json()["recommendations"]) >= 1
    first_finish_recommendation = finish.json()["recommendations"][0]
    assert "password" in first_finish_recommendation["topic_title"].lower()
    assert first_finish_recommendation["lesson_title"] == "Password manager basics"
    assert first_finish_recommendation["course_title"] == "Cyber Hygiene"
    assert first_finish_recommendation["reason"]
    recs = client.get("/api/v1/recommendations/me", headers=headers)
    assert recs.status_code == 200
    assert len(recs.json()) >= 1
    first_recommendation = recs.json()[0]
    assert "password" in first_recommendation["topic_title"].lower()
    assert first_recommendation["lesson_title"] == "Password manager basics"
    assert first_recommendation["course_title"] == "Cyber Hygiene"
    assert first_recommendation["signal_level"] in {"medium", "high"}
    history = client.get("/api/v1/attempts/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    first_attempt = history.json()[0]
    assert first_attempt["score_percent"] == 50
    assert first_attempt["course_title"] == "Cyber Hygiene"
    assert first_attempt["test_title"] == "Password Test"
    assert first_attempt["correct_answers"] == 1
    assert first_attempt["total_questions"] == 2
    assert first_attempt["weak_topics"]
    assert isinstance(first_attempt["weak_topics"][0]["topic_title"], str)
    history_paged = client.get("/api/v1/attempts/history?page=1&page_size=1", headers=headers)
    assert history_paged.status_code == 200
    history_paged_payload = history_paged.json()
    assert history_paged_payload["page"] == 1
    assert history_paged_payload["page_size"] == 1
    assert history_paged_payload["total"] >= 1
    assert len(history_paged_payload["items"]) == 1
    assert history_paged_payload["items"][0]["attempt_id"] == attempt_id
    review = client.get(f"/api/v1/attempts/{attempt_id}/review", headers=headers)
    assert review.status_code == 200
    review_payload = review.json()
    assert review_payload["attempt_id"] == attempt_id
    assert review_payload["test_title"] == "Password Test"
    assert review_payload["score_percent"] == 50
    assert len(review_payload["questions"]) == 2
    first_review_question = review_payload["questions"][0]
    assert first_review_question["question_number"] == 1
    assert first_review_question["selected_option_id"] is None
    assert first_review_question["correct_option_text"]
    assert any(option["is_correct"] for option in first_review_question["options"])
    second_review_question = review_payload["questions"][1]
    assert second_review_question["is_correct"] is True
    assert second_review_question["selected_option_text"] == second_review_question["correct_option_text"]


def test_adaptive_question_options_are_not_always_first_correct(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    start = client.post("/api/v1/tests/1/start", headers=headers)
    attempt_id = start.json()["attempt_id"]
    next_question = client.get(
        f"/api/v1/attempts/{attempt_id}/next-question", headers=headers
    ).json()
    db = SessionLocal()
    try:
        correct_option_id = (
            db.query(AnswerOption)
            .filter(
                AnswerOption.question_id == next_question["id"],
                AnswerOption.is_correct.is_(True),
            )
            .first()
            .id
        )
    finally:
        db.close()
    assert next_question["options"][0]["id"] != correct_option_id


def test_option_order_keeps_correct_answer_off_first_slot():
    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.id == 1).first()
        options = db.query(AnswerOption).filter(AnswerOption.question_id == 1).all()
        first_attempt = Attempt(
            tenant_id=1,
            test_id=1,
            user_id=3,
            current_difficulty=3,
            asked_question_ids=[],
            difficulty_path=[3],
        )
        db.add(first_attempt)
        db.commit()
        db.refresh(first_attempt)

        first_order = _ordered_options(first_attempt, question, options)

        assert first_order[0].is_correct is False
    finally:
        db.close()


def test_admin_can_assign_and_view_dashboard(client):
    headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    assign = client.post("/api/v1/courses/1/assign", headers=headers, json={"user_id": 3})
    assert assign.status_code == 200
    dashboard = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert "courses" in dashboard.json()
    assert "avg_progress" in dashboard.json()


def test_admin_sees_human_readable_problem_topics(client):
    db = SessionLocal()
    try:
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
        result = Result(tenant_id=1, attempt_id=attempt.id, score_percent=55, weak_topics=[{"topic_title": "Passwords", "score": 2}], recommendation_count=1)
        db.add(result)
        db.flush()
        recommendation = Recommendation(tenant_id=1, user_id=3, result_id=result.id, topic_id=1, lesson_id=1, priority=1, text="Repeat password hygiene")
        db.add(recommendation)
        db.commit()
    finally:
        db.close()

    headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    response = client.get("/api/v1/analytics/problem-topics", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "topic_title" in payload[0]
    assert isinstance(payload[0]["topic_title"], str)

from app.core.db import SessionLocal
from app.models.models import AnswerOption, Attempt, Question, QuestionTopic, Test, Topic
from app.services.adaptive import clamp_difficulty, evaluate_answer, select_next_question


def test_difficulty_clamps_up_and_down():
    assert clamp_difficulty(8) == 5
    assert clamp_difficulty(-1) == 1
    assert clamp_difficulty(3) == 3


def test_select_next_question_balances_topics_when_difficulty_matches():
    db = SessionLocal()
    try:
        topic_b = Topic(tenant_id=1, title="Phishing", description="Phishing signals")
        db.add(topic_b)
        db.flush()

        test = db.get(Test, 1)
        balanced_question = Question(
            tenant_id=1,
            test_id=test.id,
            text="Inspect suspicious links before clicking",
            difficulty=2,
            estimated_seconds=25,
        )
        repeated_topic_question = Question(
            tenant_id=1,
            test_id=test.id,
            text="Store secrets in the approved vault",
            difficulty=2,
            estimated_seconds=25,
        )
        db.add_all([balanced_question, repeated_topic_question])
        db.flush()

        db.add_all(
            [
                QuestionTopic(
                    tenant_id=1,
                    question_id=balanced_question.id,
                    topic_id=topic_b.id,
                ),
                QuestionTopic(
                    tenant_id=1,
                    question_id=repeated_topic_question.id,
                    topic_id=1,
                ),
            ]
        )
        attempt = Attempt(
            tenant_id=1,
            test_id=test.id,
            user_id=3,
            current_difficulty=2,
            asked_question_ids=[1],
            difficulty_path=[3, 2],
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        next_question = select_next_question(db, attempt)

        assert next_question is not None
        assert next_question.id == balanced_question.id
    finally:
        db.close()


def test_answer_feedback_uses_available_next_question_difficulty():
    db = SessionLocal()
    try:
        test = Test(
            tenant_id=1,
            course_id=1,
            title="Fallback difficulty test",
            baseline_difficulty=3,
            question_limit=2,
            is_active=True,
        )
        db.add(test)
        db.flush()
        first_question = Question(
            tenant_id=1,
            test_id=test.id,
            text="First question",
            difficulty=3,
            estimated_seconds=20,
        )
        fallback_question = Question(
            tenant_id=1,
            test_id=test.id,
            text="Fallback question",
            difficulty=3,
            estimated_seconds=20,
        )
        db.add_all([first_question, fallback_question])
        db.flush()
        correct_option = AnswerOption(
            question_id=first_question.id,
            text="Correct",
            is_correct=True,
        )
        db.add_all(
            [
                correct_option,
                AnswerOption(
                    question_id=first_question.id,
                    text="Incorrect",
                    is_correct=False,
                ),
            ]
        )
        attempt = Attempt(
            tenant_id=1,
            test_id=test.id,
            user_id=3,
            current_difficulty=3,
            asked_question_ids=[],
            difficulty_path=[3],
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        db.refresh(correct_option)

        feedback = evaluate_answer(
            db,
            attempt=attempt,
            question=first_question,
            answer_option_id=correct_option.id,
            response_seconds=10,
        )

        assert feedback["target_difficulty"] == 4
        assert feedback["current_difficulty"] == 4
        assert feedback["next_question_difficulty"] == 3
        assert attempt.difficulty_path == [3, 4]
    finally:
        db.close()

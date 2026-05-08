from collections import Counter, defaultdict
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.content_localization import review_topic_recommendation
from app.models.models import AnswerOption, Attempt, AttemptAnswer, Lesson, Question, QuestionTopic, Recommendation, Result, Tenant, Test, Topic
from app.services.recommendation_payloads import serialize_recommendations


def clamp_difficulty(value: int) -> int:
    return max(1, min(5, value))


def attempt_total_questions(db: Session, attempt: Attempt) -> int:
    test = db.get(Test, attempt.test_id)
    available_questions = db.scalar(
        select(func.count(Question.id)).where(
            Question.test_id == attempt.test_id,
            Question.tenant_id == attempt.tenant_id,
        )
    ) or 0
    return min(test.question_limit if test else available_questions, available_questions)


def question_topic_titles(db: Session, question_id: int) -> list[str]:
    topic_rows = db.execute(
        select(Topic.id, Topic.title)
        .join(QuestionTopic, QuestionTopic.topic_id == Topic.id)
        .where(QuestionTopic.question_id == question_id)
        .order_by(Topic.title)
    ).all()
    topic_ids = [topic_id for topic_id, _ in topic_rows]
    if not topic_ids:
        return []
    question = db.get(Question, question_id)
    test = db.get(Test, question.test_id) if question else None
    if test is not None:
        lesson_titles = list(
            db.scalars(
                select(Lesson.title)
                .where(
                    Lesson.tenant_id == test.tenant_id,
                    Lesson.course_id == test.course_id,
                    Lesson.topic_id.in_(topic_ids),
                )
                .order_by(Lesson.sort_order, Lesson.id)
            )
        )
        if lesson_titles:
            return lesson_titles
    return [title for _, title in topic_rows]


def select_next_question(db: Session, attempt: Attempt) -> Question | None:
    questions = db.scalars(
        select(Question).where(
            Question.test_id == attempt.test_id,
            Question.tenant_id == attempt.tenant_id,
        )
    ).all()
    remaining = [q for q in questions if q.id not in (attempt.asked_question_ids or [])]
    if not remaining:
        return None

    asked_ids = attempt.asked_question_ids or []
    topic_frequency: Counter[int] = Counter()
    if asked_ids:
        topic_frequency.update(
            db.scalars(
                select(QuestionTopic.topic_id).where(QuestionTopic.question_id.in_(asked_ids))
            )
        )

    question_topic_map: dict[int, list[int]] = defaultdict(list)
    remaining_ids = [question.id for question in remaining]
    if remaining_ids:
        for question_id, topic_id in db.execute(
            select(QuestionTopic.question_id, QuestionTopic.topic_id).where(
                QuestionTopic.question_id.in_(remaining_ids)
            )
        ).all():
            question_topic_map[question_id].append(topic_id)

    def sort_key(question: Question) -> tuple[int, int, int, int]:
        topic_ids = question_topic_map.get(question.id, [])
        if topic_ids:
            min_coverage = min(topic_frequency.get(topic_id, 0) for topic_id in topic_ids)
            total_coverage = sum(topic_frequency.get(topic_id, 0) for topic_id in topic_ids)
        else:
            min_coverage = 0
            total_coverage = 0
        return (
            abs(question.difficulty - attempt.current_difficulty),
            min_coverage,
            total_coverage,
            question.id,
        )

    return sorted(remaining, key=sort_key)[0]


def _recommendation_lesson_id(
    db: Session, *, tenant_id: int, course_id: int, topic_id: int
) -> int | None:
    return db.scalar(
        select(Lesson.id)
        .where(
            Lesson.tenant_id == tenant_id,
            Lesson.course_id == course_id,
            Lesson.topic_id == topic_id,
        )
        .order_by(Lesson.sort_order, Lesson.id)
        .limit(1)
    )


def evaluate_answer(
    db: Session,
    *,
    attempt: Attempt,
    question: Question,
    answer_option_id: int | None,
    response_seconds: int,
) -> dict:
    options = db.scalars(select(AnswerOption).where(AnswerOption.question_id == question.id)).all()
    option_ids = {option.id for option in options}
    if answer_option_id is not None and answer_option_id not in option_ids:
        raise HTTPException(status_code=422, detail="Answer option does not belong to question")
    correct_option = next((opt for opt in options if opt.is_correct), None)
    is_correct = bool(correct_option and correct_option.id == answer_option_id)
    previous_difficulty = attempt.current_difficulty
    attempt.asked_question_ids = [*(attempt.asked_question_ids or []), question.id]
    attempt.current_difficulty = clamp_difficulty(attempt.current_difficulty + (1 if is_correct else -1))
    attempt.difficulty_path = [*(attempt.difficulty_path or []), attempt.current_difficulty]
    answer = AttemptAnswer(
        tenant_id=attempt.tenant_id,
        attempt_id=attempt.id,
        question_id=question.id,
        answer_option_id=answer_option_id,
        is_correct=is_correct,
        response_seconds=response_seconds,
    )
    db.add(answer)
    total_questions = attempt_total_questions(db, attempt)
    answered_questions = len(attempt.asked_question_ids or [])
    return {
        "is_correct": is_correct,
        "previous_difficulty": previous_difficulty,
        "current_difficulty": attempt.current_difficulty,
        "answered_questions": answered_questions,
        "total_questions": total_questions,
        "remaining_questions": max(total_questions - answered_questions, 0),
        "correct_option_id": correct_option.id if correct_option else None,
        "correct_option_text": correct_option.text if correct_option else None,
        "explanation": question.explanation or "",
        "topic_titles": question_topic_titles(db, question.id),
    }

def _attempt_summary(db: Session, attempt: Attempt, result: Result) -> dict:
    answers = db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)).all()
    correct_answers = len([answer for answer in answers if answer.is_correct])
    total_questions = len(answers)
    average_response_seconds = (
        int(sum(answer.response_seconds for answer in answers) / len(answers))
        if answers
        else 0
    )
    recommendations = db.scalars(
        select(Recommendation)
        .where(Recommendation.result_id == result.id)
        .order_by(Recommendation.priority, Recommendation.id)
    ).all()
    tenant_locale = db.scalar(select(Tenant.locale).where(Tenant.id == attempt.tenant_id))
    return {
        "result": result,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "average_response_seconds": average_response_seconds,
        "final_difficulty": attempt.current_difficulty,
        "difficulty_path": attempt.difficulty_path or [],
        "recommendations": serialize_recommendations(db, recommendations, tenant_locale),
    }


def finalize_attempt(db: Session, attempt: Attempt) -> dict:
    existing_result = db.scalar(select(Result).where(Result.attempt_id == attempt.id))
    if existing_result is not None:
        attempt.status = "finished"
        attempt.finished_at = attempt.finished_at or datetime.utcnow()
        return _attempt_summary(db, attempt, existing_result)

    answers = db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)).all()
    total = len(answers) or 1
    correct = len([item for item in answers if item.is_correct])
    result = Result(
        tenant_id=attempt.tenant_id,
        attempt_id=attempt.id,
        score_percent=int(correct * 100 / total),
        weak_topics=[],
    )
    tenant_locale = db.scalar(select(Tenant.locale).where(Tenant.id == attempt.tenant_id))
    test = db.get(Test, attempt.test_id)
    lesson_topic_titles: dict[int, str] = {}
    if test is not None:
        lesson_topic_titles = {
            topic_id: title
            for topic_id, title in db.execute(
                select(Lesson.topic_id, Lesson.title).where(
                    Lesson.tenant_id == attempt.tenant_id,
                    Lesson.course_id == test.course_id,
                    Lesson.topic_id.is_not(None),
                )
            ).all()
        }
    weak_topic_scores: Counter[int] = Counter()
    db.add(result)
    db.flush()
    question_ids = list({answer.question_id for answer in answers})
    questions = (
        db.scalars(
            select(Question).where(
                Question.id.in_(question_ids),
                Question.tenant_id == attempt.tenant_id,
            )
        ).all()
        if question_ids
        else []
    )
    question_by_id = {question.id: question for question in questions}
    question_topics_map: dict[int, list[int]] = defaultdict(list)
    if question_ids:
        for question_id, topic_id in db.execute(
            select(QuestionTopic.question_id, QuestionTopic.topic_id).where(
                QuestionTopic.question_id.in_(question_ids),
                QuestionTopic.tenant_id == attempt.tenant_id,
            )
        ).all():
            question_topics_map[question_id].append(topic_id)
    for answer in answers:
        question = question_by_id.get(answer.question_id)
        if question is None:
            continue
        topic_ids = question_topics_map.get(question.id, [])
        if not topic_ids:
            continue
        base_penalty = (0 if answer.is_correct else 2) + (
            1 if answer.response_seconds > question.estimated_seconds else 0
        )
        per_topic_penalty = base_penalty / len(topic_ids)
        for topic_id in topic_ids:
            weak_topic_scores[topic_id] += per_topic_penalty
    weak_topics = []
    for priority, (topic_id, score) in enumerate(weak_topic_scores.most_common(5), start=1):
        if score <= 0:
            continue
        topic = db.get(Topic, topic_id)
        display_topic_title = lesson_topic_titles.get(topic_id) or (topic.title if topic else "Unknown")
        weak_topics.append(
            {
                "topic_id": topic_id,
                "topic_title": display_topic_title,
                "score": score,
            }
        )
        db.add(
            Recommendation(
                tenant_id=attempt.tenant_id,
                user_id=attempt.user_id,
                result_id=result.id,
                topic_id=topic_id,
                lesson_id=_recommendation_lesson_id(
                    db,
                    tenant_id=attempt.tenant_id,
                    course_id=test.course_id if test else 0,
                    topic_id=topic_id,
                )
                if test
                else None,
                priority=priority,
                text=review_topic_recommendation(
                    tenant_locale, display_topic_title
                ),
            )
        )
    result.weak_topics = weak_topics
    result.recommendation_count = len(weak_topics)
    attempt.status = "finished"
    attempt.finished_at = datetime.utcnow()
    db.flush()
    return _attempt_summary(db, attempt, result)

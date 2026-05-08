import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.models.models import (
    AnswerOption,
    Attempt,
    AttemptAnswer,
    Course,
    Lesson,
    Membership,
    Question,
    QuestionTopic,
    Result,
    RoleName,
    Tenant,
    Test,
    Topic,
)
from app.schemas.testing import QuestionCreate, QuestionOptionRead, QuestionRead, SubmitAnswerRequest, TestCreate, TestUpdate
from app.services.adaptive import attempt_total_questions, evaluate_answer, finalize_attempt, question_topic_titles, select_next_question

router = APIRouter(tags=["tests"])


def _ordered_options(
    attempt: Attempt, question: Question, options: list[AnswerOption]
) -> list[AnswerOption]:
    ordered_by_id = sorted(options, key=lambda option: option.id)
    if len(options) < 2:
        return ordered_by_id

    if not question.shuffle_options:
        return ordered_by_id

    ordered = sorted(
        options,
        key=lambda option: hashlib.sha256(
            f"{attempt.id}:{question.id}:{option.id}".encode()
        ).hexdigest(),
    )
    if ordered[0].is_correct:
        ordered = ordered[1:] + ordered[:1]
    return ordered


def _serialize_question(db: Session, tenant_id: int, question: Question) -> dict:
    options = db.scalars(select(AnswerOption).where(AnswerOption.question_id == question.id).order_by(AnswerOption.id.asc())).all()
    topic_rows = db.execute(
        select(Topic.id, Topic.title)
        .join(QuestionTopic, QuestionTopic.topic_id == Topic.id)
        .where(QuestionTopic.tenant_id == tenant_id, QuestionTopic.question_id == question.id)
        .order_by(Topic.title.asc(), Topic.id.asc())
    ).all()
    topic_ids = [topic_id for topic_id, _ in topic_rows]
    test = db.scalar(select(Test).where(Test.id == question.test_id, Test.tenant_id == tenant_id))
    lesson_rows: list[tuple[int, str]] = []
    if test is not None and topic_ids:
        lesson_rows = db.execute(
            select(Lesson.id, Lesson.title)
            .where(
                Lesson.tenant_id == tenant_id,
                Lesson.course_id == test.course_id,
                Lesson.topic_id.in_(topic_ids),
            )
            .order_by(Lesson.sort_order.asc(), Lesson.id.asc())
        ).all()
    if lesson_rows:
        resolved_topic_ids = [lesson_id for lesson_id, _ in lesson_rows]
        resolved_topic_titles = [title for _, title in lesson_rows]
    else:
        resolved_topic_ids = topic_ids
        resolved_topic_titles = [title for _, title in topic_rows]
    return {
        "id": question.id,
        "test_id": question.test_id,
        "text": question.text,
        "explanation": question.explanation,
        "difficulty": question.difficulty,
        "estimated_seconds": question.estimated_seconds,
        "shuffle_options": question.shuffle_options,
        "option_count": len(options),
        "options": [{"id": item.id, "text": item.text, "is_correct": item.is_correct} for item in options],
        "topic_ids": resolved_topic_ids,
        "topic_titles": resolved_topic_titles,
    }


def _sync_question(question: Question, payload: QuestionCreate, tenant: Tenant, db: Session) -> None:
    question.test_id = payload.test_id
    question.text = payload.text
    question.explanation = payload.explanation
    question.difficulty = payload.difficulty
    question.estimated_seconds = payload.estimated_seconds
    question.shuffle_options = payload.shuffle_options
    test = db.scalar(select(Test).where(Test.id == question.test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    db.execute(delete(AnswerOption).where(AnswerOption.question_id == question.id))
    db.execute(delete(QuestionTopic).where(QuestionTopic.tenant_id == tenant.id, QuestionTopic.question_id == question.id))
    db.flush()
    for option in payload.options:
        db.add(AnswerOption(question_id=question.id, text=option["text"], is_correct=option.get("is_correct", False)))
    resolved_topic_ids: list[int] = []
    for lesson_id in payload.topic_ids:
        lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.tenant_id == tenant.id))
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
        if lesson.course_id != test.course_id:
            raise HTTPException(status_code=422, detail="Lesson does not belong to test course")
        if lesson.topic_id is None:
            topic = Topic(
                tenant_id=tenant.id,
                title=lesson.title,
                description=lesson.summary or "",
            )
            db.add(topic)
            db.flush()
            lesson.topic_id = topic.id
        else:
            topic = db.get(Topic, lesson.topic_id)
            if topic is not None and topic.tenant_id == tenant.id:
                topic.title = lesson.title
                topic.description = lesson.summary or ""
        resolved_topic_ids.append(lesson.topic_id)
    for topic_id in dict.fromkeys(resolved_topic_ids):
        db.add(QuestionTopic(tenant_id=tenant.id, question_id=question.id, topic_id=topic_id))


@router.get("/tests")
def list_tests(_: Membership = Depends(active_membership), tenant: Tenant = Depends(tenant_context), db: Session = Depends(get_db)) -> list[dict]:
    tests = db.scalars(
        select(Test)
        .where(Test.tenant_id == tenant.id)
        .order_by(Test.course_id.asc(), Test.is_active.desc(), Test.id.asc())
    ).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "course_id": item.course_id,
            "baseline_difficulty": item.baseline_difficulty,
            "question_limit": item.question_limit,
            "is_active": item.is_active,
            "question_count": db.scalar(
                select(func.count(Question.id)).where(
                    Question.test_id == item.id,
                    Question.tenant_id == tenant.id,
                )
            ) or 0,
        }
        for item in tests
    ]


@router.get("/topics")
def list_topics(
    course_id: int | None = None,
    _: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    if course_id is not None:
        course = db.scalar(select(Course.id).where(Course.id == course_id, Course.tenant_id == tenant.id))
        if course is None:
            raise HTTPException(status_code=404, detail="Course not found")
        lessons = db.scalars(
            select(Lesson)
            .where(Lesson.tenant_id == tenant.id, Lesson.course_id == course_id)
            .order_by(Lesson.sort_order.asc(), Lesson.id.asc())
        ).all()
        return [{"id": item.id, "title": item.title, "description": item.summary or ""} for item in lessons]
    topics = db.scalars(select(Topic).where(Topic.tenant_id == tenant.id).order_by(Topic.title.asc())).all()
    return [{"id": item.id, "title": item.title, "description": item.description} for item in topics]


@router.get("/questions")
def list_questions(
    test_id: int,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    _: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict] | dict:
    base_query = select(Question).where(Question.tenant_id == tenant.id, Question.test_id == test_id)
    if page is None and page_size is None:
        questions = db.scalars(base_query.order_by(Question.id.asc())).all()
        return [_serialize_question(db, tenant.id, item) for item in questions]

    resolved_page = page or 1
    resolved_page_size = page_size or 20
    total = db.scalar(
        select(func.count(Question.id)).where(
            Question.tenant_id == tenant.id,
            Question.test_id == test_id,
        )
    ) or 0
    questions = db.scalars(
        base_query
        .order_by(Question.id.asc())
        .offset((resolved_page - 1) * resolved_page_size)
        .limit(resolved_page_size)
    ).all()
    return {
        "items": [_serialize_question(db, tenant.id, item) for item in questions],
        "page": resolved_page,
        "page_size": resolved_page_size,
        "total": total,
    }


@router.post("/tests")
def create_test(
    payload: TestCreate,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    course = db.scalar(select(Course.id).where(Course.id == payload.course_id, Course.tenant_id == tenant.id))
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    has_active_for_course = db.scalar(
        select(func.count(Test.id)).where(
            Test.tenant_id == tenant.id,
            Test.course_id == payload.course_id,
            Test.is_active.is_(True),
        )
    ) or 0
    test = Test(
        tenant_id=tenant.id,
        course_id=payload.course_id,
        title=payload.title,
        baseline_difficulty=payload.baseline_difficulty,
        question_limit=payload.question_limit,
        is_active=has_active_for_course == 0,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return {"id": test.id, "title": test.title}


@router.patch("/tests/{test_id}")
def update_test(
    test_id: int,
    payload: TestUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    test = db.scalar(select(Test).where(Test.id == test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")

    test.title = payload.title
    test.baseline_difficulty = payload.baseline_difficulty
    test.question_limit = payload.question_limit

    write_audit_log(db, action="tests.update", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="test", entity_id=test.id)
    db.commit()
    db.refresh(test)
    return {
        "id": test.id,
        "title": test.title,
        "baseline_difficulty": test.baseline_difficulty,
        "question_limit": test.question_limit,
        "is_active": test.is_active,
    }


@router.post("/tests/{test_id}/activate")
def activate_test(
    test_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    test = db.scalar(select(Test).where(Test.id == test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")

    sibling_tests = db.scalars(
        select(Test).where(
            Test.tenant_id == tenant.id,
            Test.course_id == test.course_id,
        )
    ).all()
    for sibling in sibling_tests:
        sibling.is_active = sibling.id == test.id

    write_audit_log(db, action="tests.activate", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="test", entity_id=test.id)
    db.commit()
    return {"id": test.id, "is_active": True}


@router.delete("/tests/{test_id}")
def delete_test(
    test_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    test = db.scalar(select(Test).where(Test.id == test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")

    attempts_count = db.scalar(select(func.count(Attempt.id)).where(Attempt.test_id == test.id, Attempt.tenant_id == tenant.id)) or 0
    if attempts_count > 0:
        raise HTTPException(status_code=409, detail="Test has attempts")

    question_ids = db.scalars(select(Question.id).where(Question.test_id == test.id, Question.tenant_id == tenant.id)).all()
    if question_ids:
        db.execute(delete(AnswerOption).where(AnswerOption.question_id.in_(question_ids)))
        db.execute(delete(QuestionTopic).where(QuestionTopic.tenant_id == tenant.id, QuestionTopic.question_id.in_(question_ids)))
        db.execute(delete(Question).where(Question.id.in_(question_ids)))

    was_active = bool(test.is_active)
    course_id = test.course_id
    db.delete(test)
    write_audit_log(db, action="tests.delete", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="test", entity_id=test.id)
    db.flush()
    if was_active:
        fallback = db.scalar(
            select(Test)
            .where(Test.tenant_id == tenant.id, Test.course_id == course_id)
            .order_by(Test.id.asc())
        )
        if fallback is not None:
            fallback.is_active = True
    db.commit()
    return {"deleted": True}


@router.post("/questions")
def create_question(
    payload: QuestionCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    test = db.scalar(select(Test.id).where(Test.id == payload.test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    question = Question(tenant_id=tenant.id, test_id=payload.test_id, text=payload.text, explanation=payload.explanation, difficulty=payload.difficulty, estimated_seconds=payload.estimated_seconds, shuffle_options=payload.shuffle_options)
    db.add(question)
    db.flush()
    _sync_question(question, payload, tenant, db)
    write_audit_log(db, action="questions.create", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="question", entity_id=question.id)
    db.commit()
    return {"id": question.id}


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    payload: QuestionCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    question = db.scalar(select(Question).where(Question.id == question_id, Question.tenant_id == tenant.id))
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    target_test = db.scalar(select(Test.id).where(Test.id == payload.test_id, Test.tenant_id == tenant.id))
    if target_test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    _sync_question(question, payload, tenant, db)
    write_audit_log(db, action="questions.update", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="question", entity_id=question.id)
    db.commit()
    db.refresh(question)
    return _serialize_question(db, tenant.id, question)


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    question = db.scalar(select(Question).where(Question.id == question_id, Question.tenant_id == tenant.id))
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    attempts_count = db.scalar(
        select(func.count(AttemptAnswer.id)).where(AttemptAnswer.question_id == question.id, AttemptAnswer.tenant_id == tenant.id)
    ) or 0
    if attempts_count > 0:
        raise HTTPException(status_code=409, detail="Question is used in attempts")

    db.execute(delete(AnswerOption).where(AnswerOption.question_id == question.id))
    db.execute(delete(QuestionTopic).where(QuestionTopic.tenant_id == tenant.id, QuestionTopic.question_id == question.id))
    db.execute(delete(Question).where(Question.id == question.id, Question.tenant_id == tenant.id))

    write_audit_log(db, action="questions.delete", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="question", entity_id=question.id)
    db.commit()
    return {"deleted": True}


@router.post("/tests/{test_id}/start")
def start_test(
    test_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    test = db.scalar(select(Test).where(Test.id == test_id, Test.tenant_id == tenant.id))
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    question_count = db.scalar(
        select(func.count(Question.id)).where(
            Question.test_id == test.id,
            Question.tenant_id == tenant.id,
        )
    ) or 0
    if question_count == 0:
        raise HTTPException(status_code=400, detail="Test has no questions")
    attempt = Attempt(tenant_id=tenant.id, test_id=test.id, user_id=membership.user_id, current_difficulty=test.baseline_difficulty, asked_question_ids=[], difficulty_path=[test.baseline_difficulty])
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "question_limit": attempt_total_questions(db, attempt),
        "baseline_difficulty": test.baseline_difficulty,
    }


@router.get("/attempts/history")
def attempt_history(
    course_id: int | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[dict] | dict:
    query = (
        select(
            Attempt.id,
            Attempt.started_at,
            Attempt.finished_at,
            Attempt.current_difficulty,
            Attempt.difficulty_path,
            Test.id,
            Test.title,
            Course.id,
            Course.title,
            Result.score_percent,
            Result.weak_topics,
            Result.recommendation_count,
        )
        .join(Result, Result.attempt_id == Attempt.id)
        .join(Test, Test.id == Attempt.test_id)
        .join(Course, Course.id == Test.course_id)
        .where(
            Attempt.tenant_id == tenant.id,
            Attempt.user_id == membership.user_id,
        )
        .order_by(Attempt.finished_at.desc(), Attempt.id.desc())
    )
    if course_id is not None:
        query = query.where(Course.id == course_id)
    resolved_page = page or 1
    resolved_page_size = page_size or 20
    if page is None and page_size is None:
        rows = db.execute(query).all()
        total = len(rows)
    else:
        count_query = (
            select(func.count(Attempt.id))
            .join(Result, Result.attempt_id == Attempt.id)
            .join(Test, Test.id == Attempt.test_id)
            .join(Course, Course.id == Test.course_id)
            .where(
                Attempt.tenant_id == tenant.id,
                Attempt.user_id == membership.user_id,
            )
        )
        if course_id is not None:
            count_query = count_query.where(Course.id == course_id)
        total = db.scalar(count_query) or 0
        rows = db.execute(
            query
            .offset((resolved_page - 1) * resolved_page_size)
            .limit(resolved_page_size)
        ).all()
    if not rows:
        if page is None and page_size is None:
            return []
        return {
            "items": [],
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        }

    attempt_ids = [row[0] for row in rows]
    answer_stats = {
        attempt_id: {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "average_response_seconds": int(round(average_seconds or 0)),
        }
        for attempt_id, total_questions, correct_answers, average_seconds in db.execute(
            select(
                AttemptAnswer.attempt_id,
                func.count(AttemptAnswer.id),
                func.sum(
                    case((AttemptAnswer.is_correct.is_(True), 1), else_=0)
                ),
                func.avg(AttemptAnswer.response_seconds),
            )
            .where(AttemptAnswer.attempt_id.in_(attempt_ids))
            .group_by(AttemptAnswer.attempt_id)
        ).all()
    }

    payload = []
    for row in rows:
        (
            attempt_id,
            started_at,
            finished_at,
            current_difficulty,
            difficulty_path,
            test_id,
            test_title,
            resolved_course_id,
            course_title,
            score_percent,
            weak_topics,
            recommendation_count,
        ) = row
        stats = answer_stats.get(
            attempt_id,
            {
                "total_questions": 0,
                "correct_answers": 0,
                "average_response_seconds": 0,
            },
        )
        payload.append(
            {
                "attempt_id": attempt_id,
                "test_id": test_id,
                "test_title": test_title,
                "course_id": resolved_course_id,
                "course_title": course_title,
                "score_percent": score_percent,
                "correct_answers": stats["correct_answers"],
                "total_questions": stats["total_questions"],
                "average_response_seconds": stats["average_response_seconds"],
                "final_difficulty": current_difficulty,
                "difficulty_path": difficulty_path or [],
                "weak_topics": weak_topics or [],
                "recommendation_count": recommendation_count,
                "started_at": started_at,
                "finished_at": finished_at,
            }
        )
    if page is None and page_size is None:
        return payload
    return {
        "items": payload,
        "page": resolved_page,
        "page_size": resolved_page_size,
        "total": total,
    }


@router.get("/attempts/{attempt_id}/review")
def attempt_review(
    attempt_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(
        select(
            Attempt,
            Test,
            Course,
            Result,
        )
        .join(Result, Result.attempt_id == Attempt.id)
        .join(Test, Test.id == Attempt.test_id)
        .join(Course, Course.id == Test.course_id)
        .where(
            Attempt.id == attempt_id,
            Attempt.tenant_id == tenant.id,
            Attempt.user_id == membership.user_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attempt, test, course, result = row
    answers = db.scalars(
        select(AttemptAnswer)
        .where(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.id)
    ).all()
    question_ids_in_order = list(attempt.asked_question_ids or [])
    for answer in answers:
        if answer.question_id not in question_ids_in_order:
            question_ids_in_order.append(answer.question_id)

    if question_ids_in_order:
        questions = db.scalars(
            select(Question).where(
                Question.id.in_(question_ids_in_order),
                Question.tenant_id == tenant.id,
            )
        ).all()
        option_rows = db.scalars(
            select(AnswerOption).where(AnswerOption.question_id.in_(question_ids_in_order))
        ).all()
    else:
        questions = []
        option_rows = []

    question_by_id = {question.id: question for question in questions}
    answer_by_question_id = {answer.question_id: answer for answer in answers}
    options_by_question_id: dict[int, list[AnswerOption]] = {}
    for option in option_rows:
        options_by_question_id.setdefault(option.question_id, []).append(option)

    review_questions = []
    for index, question_id in enumerate(question_ids_in_order, start=1):
        question = question_by_id.get(question_id)
        answer = answer_by_question_id.get(question_id)
        if question is None or answer is None:
            continue
        ordered_options = _ordered_options(
            attempt,
            question,
            options_by_question_id.get(question.id, []),
        )
        correct_option = next((option for option in ordered_options if option.is_correct), None)
        selected_option = next(
            (option for option in ordered_options if option.id == answer.answer_option_id),
            None,
        )
        review_questions.append(
            {
                "question_id": question.id,
                "question_number": index,
                "text": question.text,
                "difficulty": question.difficulty,
                "response_seconds": answer.response_seconds,
                "is_correct": answer.is_correct,
                "explanation": question.explanation or "",
                "topic_titles": question_topic_titles(db, question.id),
                "selected_option_id": selected_option.id if selected_option else None,
                "selected_option_text": selected_option.text if selected_option else "",
                "correct_option_id": correct_option.id if correct_option else None,
                "correct_option_text": correct_option.text if correct_option else "",
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "is_selected": option.id == answer.answer_option_id,
                        "is_correct": option.is_correct,
                    }
                    for option in ordered_options
                ],
            }
        )

    correct_answers = len([answer for answer in answers if answer.is_correct])
    average_response_seconds = (
        int(round(sum(answer.response_seconds for answer in answers) / len(answers)))
        if answers
        else 0
    )
    return {
        "attempt_id": attempt.id,
        "test_id": test.id,
        "test_title": test.title,
        "course_id": course.id,
        "course_title": course.title,
        "score_percent": result.score_percent,
        "correct_answers": correct_answers,
        "total_questions": len(review_questions),
        "average_response_seconds": average_response_seconds,
        "final_difficulty": attempt.current_difficulty,
        "difficulty_path": attempt.difficulty_path or [],
        "weak_topics": result.weak_topics or [],
        "started_at": attempt.started_at,
        "finished_at": attempt.finished_at,
        "questions": review_questions,
    }


@router.get("/attempts/{attempt_id}/next-question", response_model=QuestionRead | None)
def next_question(
    attempt_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> QuestionRead | None:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id, Attempt.tenant_id == tenant.id, Attempt.user_id == membership.user_id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    total_questions = attempt_total_questions(db, attempt)
    if len(attempt.asked_question_ids or []) >= total_questions:
        return None
    question = select_next_question(db, attempt)
    if question is None:
        return None
    options = db.scalars(
        select(AnswerOption).where(AnswerOption.question_id == question.id)
    ).all()
    ordered_options = _ordered_options(attempt, question, options)
    answered_questions = len(attempt.asked_question_ids or [])
    return QuestionRead(
        id=question.id,
        text=question.text,
        difficulty=question.difficulty,
        estimated_seconds=question.estimated_seconds,
        question_number=answered_questions + 1,
        total_questions=total_questions,
        remaining_questions=max(total_questions - answered_questions - 1, 0),
        # Show the effective level actually used to pick this question.
        # If an exact target level is unavailable in the remaining pool,
        # the selected question can be from the nearest level instead.
        target_difficulty=question.difficulty,
        topic_titles=question_topic_titles(db, question.id),
        options=[QuestionOptionRead(id=opt.id, text=opt.text) for opt in ordered_options],
    )


@router.post("/attempts/{attempt_id}/submit-answer")
def submit_answer(
    attempt_id: int,
    payload: SubmitAnswerRequest,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id, Attempt.tenant_id == tenant.id, Attempt.user_id == membership.user_id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.status == "finished":
        raise HTTPException(status_code=409, detail="Attempt already finished")
    current_question = select_next_question(db, attempt)
    if current_question is None:
        raise HTTPException(status_code=400, detail="No question available")
    if current_question.id != payload.question_id:
        raise HTTPException(status_code=409, detail="Question is no longer current")
    feedback = evaluate_answer(
        db,
        attempt=attempt,
        question=current_question,
        answer_option_id=payload.answer_option_id,
        response_seconds=payload.response_seconds,
    )
    db.commit()
    return feedback


@router.post("/attempts/{attempt_id}/finish")
def finish_attempt(
    attempt_id: int,
    membership: Membership = Depends(active_membership),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id, Attempt.tenant_id == tenant.id, Attempt.user_id == membership.user_id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.status == "finished":
        raise HTTPException(status_code=409, detail="Attempt already finished")
    summary = finalize_attempt(db, attempt)
    write_audit_log(db, action="tests.finish", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="attempt", entity_id=attempt.id)
    db.commit()
    result = summary["result"]
    return {
        "score_percent": result.score_percent,
        "weak_topics": result.weak_topics,
        "recommendation_count": result.recommendation_count,
        "recommendations": summary["recommendations"],
        "correct_answers": summary["correct_answers"],
        "total_questions": summary["total_questions"],
        "average_response_seconds": summary["average_response_seconds"],
        "final_difficulty": summary["final_difficulty"],
        "difficulty_path": summary["difficulty_path"],
    }

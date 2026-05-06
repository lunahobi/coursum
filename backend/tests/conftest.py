import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["LMS_DATABASE_URL"] = "sqlite:///./test.db"

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import AnswerOption, Course, Enrollment, Lesson, Membership, Question, QuestionTopic, Role, RoleName, Tenant, Test, Topic, User  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    if engine.url.get_backend_name() == "sqlite":
        engine.dispose()
        db_path = Path("test.db")
        if db_path.exists():
            db_path.unlink()
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    roles = [Role(name=role.value, description=role.value) for role in RoleName]
    db.add_all(roles)
    db.flush()
    role_map = {role.name: role for role in roles}
    tenant_a = Tenant(name="Tenant A", code="tenant-a", locale="ru")
    tenant_b = Tenant(name="Tenant B", code="tenant-b", locale="en")
    tenant_c = Tenant(name="Tenant C", code="tenant-c", locale="en")
    db.add_all([tenant_a, tenant_b, tenant_c])
    db.flush()
    users = {
        "admin_a": User(email="admin-a@example.com", full_name="Admin A", password_hash=hash_password("Password123!")),
        "teacher_a": User(email="teacher-a@example.com", full_name="Teacher A", password_hash=hash_password("Password123!")),
        "learner_a": User(email="learner-a@example.com", full_name="Learner A", password_hash=hash_password("Password123!")),
        "learner_b": User(email="learner-b@example.com", full_name="Learner B", password_hash=hash_password("Password123!")),
        "teacher_b": User(email="teacher-b@example.com", full_name="Teacher B", password_hash=hash_password("Password123!")),
    }
    db.add_all(users.values())
    db.flush()
    db.add_all(
        [
            Membership(user_id=users["admin_a"].id, tenant_id=tenant_a.id, role_id=role_map[RoleName.org_admin.value].id, is_active=True),
            Membership(user_id=users["teacher_a"].id, tenant_id=tenant_a.id, role_id=role_map[RoleName.teacher.value].id, is_active=True),
            Membership(user_id=users["teacher_b"].id, tenant_id=tenant_b.id, role_id=role_map[RoleName.teacher.value].id, is_active=True),
            Membership(user_id=users["learner_a"].id, tenant_id=tenant_a.id, role_id=role_map[RoleName.learner.value].id, is_active=True),
            Membership(user_id=users["learner_b"].id, tenant_id=tenant_b.id, role_id=role_map[RoleName.learner.value].id, is_active=True),
        ]
    )
    course = Course(tenant_id=tenant_a.id, title="Cyber Hygiene", description="Core security", created_by_id=users["teacher_a"].id)
    course_b = Course(tenant_id=tenant_b.id, title="Service workflow", description="Tenant B course", created_by_id=users["teacher_b"].id)
    db.add(course)
    db.add(course_b)
    db.flush()
    db.add(Enrollment(tenant_id=tenant_a.id, course_id=course.id, user_id=users["learner_a"].id, progress_percent=0, completed=False))
    db.add(Enrollment(tenant_id=tenant_b.id, course_id=course_b.id, user_id=users["learner_b"].id, progress_percent=40, completed=False))
    topic = Topic(tenant_id=tenant_a.id, title="Passwords", description="Password management")
    db.add(topic)
    db.flush()
    db.add_all(
        [
            Lesson(
                tenant_id=tenant_a.id,
                course_id=course.id,
                topic_id=topic.id,
                title="Password manager basics",
                summary="Why a password manager reduces reuse risk.",
                content="## Overview\nUnderstand why unique credentials matter.\n\n## Practice\nStore and generate unique passwords in one tool.",
                content_pages=[
                    {
                        "page_id": "passwords-overview",
                        "chapter_title": "Password hygiene",
                        "page_title": "Why password managers matter",
                        "blocks": [
                            {"type": "text", "text": "A password manager helps generate and store unique passwords."},
                            {"type": "video", "url": "https://cdn.example.com/passwords.mp4", "title": "Password manager walkthrough"},
                        ],
                    },
                    {
                        "page_id": "passwords-practice",
                        "chapter_title": "Password hygiene",
                        "page_title": "Practice checklist",
                        "blocks": [{"type": "text", "text": "Install the approved tool, import accounts, and enable MFA."}],
                    },
                ],
                duration_minutes=9,
                video_url="https://cdn.example.com/passwords.mp4",
                sort_order=1,
            ),
            Lesson(
                tenant_id=tenant_a.id,
                course_id=course.id,
                topic_id=topic.id,
                title="Phishing basics",
                summary="How to slow down and inspect suspicious messages.",
                content="## Spot the signal\nCheck sender, domain, and urgency.\n\n## Next step\nReport suspicious messages through the approved channel.",
                duration_minutes=7,
                sort_order=2,
            ),
        ]
    )
    test = Test(tenant_id=tenant_a.id, course_id=course.id, title="Password Test", baseline_difficulty=3, question_limit=2)
    db.add(test)
    db.flush()
    question1 = Question(tenant_id=tenant_a.id, test_id=test.id, text="Use a password manager?", difficulty=3, estimated_seconds=30)
    question2 = Question(tenant_id=tenant_a.id, test_id=test.id, text="Rotate passwords monthly?", difficulty=4, estimated_seconds=20)
    db.add_all([question1, question2])
    db.flush()
    db.add_all([QuestionTopic(tenant_id=tenant_a.id, question_id=question1.id, topic_id=topic.id), QuestionTopic(tenant_id=tenant_a.id, question_id=question2.id, topic_id=topic.id)])
    db.add_all(
        [
            AnswerOption(question_id=question1.id, text="Yes", is_correct=True),
            AnswerOption(question_id=question1.id, text="No", is_correct=False),
            AnswerOption(question_id=question2.id, text="No", is_correct=True),
            AnswerOption(question_id=question2.id, text="Yes", is_correct=False),
        ]
    )
    db.commit()
    db.close()
    yield
    if engine.url.get_backend_name() == "sqlite":
        engine.dispose()
        db_path = Path("test.db")
        if db_path.exists():
            db_path.unlink()
    else:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client: TestClient, email: str, tenant_code: str) -> dict[str, str]:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Tenant-Code": tenant_code, "Host": "localhost"}

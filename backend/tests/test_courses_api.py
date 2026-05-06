from app.core.db import SessionLocal
from app.models.models import Course

from .conftest import auth_headers


def test_course_cover_persists_on_create_and_update(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    created = client.post(
        "/api/v1/courses",
        headers=teacher_headers,
        json={
            "title": "Support onboarding",
            "description": "New learner journey",
            "image_url": "/media/support-onboarding.png",
        },
    )
    assert created.status_code == 200
    assert created.json()["image_url"] == "/media/support-onboarding.png"

    course_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/courses/{course_id}",
        headers=teacher_headers,
        json={
            "title": "Support onboarding",
            "description": "Updated learner journey",
            "image_url": "/media/support-onboarding-v2.png",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["image_url"] == "/media/support-onboarding-v2.png"


def test_learner_only_sees_courses_after_assignment(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={
            "title": "Manager communication",
            "description": "Not assigned yet",
            "image_url": "/media/manager-communication.png",
            "status": "published",
        },
    )
    assert created.status_code == 200
    course_id = created.json()["id"]

    learner_courses = client.get("/api/v1/courses", headers=learner_headers)
    assert learner_courses.status_code == 200
    assert all(item["id"] != course_id for item in learner_courses.json())

    users = client.get("/api/v1/users", headers=admin_headers)
    learner_id = next(item["id"] for item in users.json() if item["email"] == "learner-a@example.com")

    assigned = client.post(
        f"/api/v1/courses/{course_id}/assign",
        headers=admin_headers,
        json={"user_id": learner_id},
    )
    assert assigned.status_code == 200

    learner_courses_after_assignment = client.get("/api/v1/courses", headers=learner_headers)
    assert learner_courses_after_assignment.status_code == 200
    assert any(item["id"] == course_id for item in learner_courses_after_assignment.json())


def test_learner_does_not_see_draft_course_even_if_is_published_true(client):
    """
    Learners must only see courses with status='published'.
    Even inconsistent legacy flags (is_published=True + status='draft')
    must remain hidden.
    """
    db = SessionLocal()
    try:
        course = db.get(Course, 1)
        assert course is not None
        course.status = "draft"
        course.is_published = True
        db.add(course)
        db.commit()
    finally:
        db.close()

    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    response = client.get("/api/v1/courses", headers=learner_headers)
    assert response.status_code == 200
    payload = response.json()
    assert all(item["id"] != 1 for item in payload)

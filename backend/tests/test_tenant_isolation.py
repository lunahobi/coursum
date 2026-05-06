from .conftest import auth_headers


def test_cross_tenant_course_access_denied(client):
    response = client.get("/api/v1/courses/1", headers=auth_headers(client, "learner-b@example.com", "tenant-b"))
    assert response.status_code == 404


def test_membership_required_for_current_tenant(client):
    response = client.get("/api/v1/courses", headers=auth_headers(client, "learner-a@example.com", "tenant-b"))
    assert response.status_code == 403


def test_teacher_sees_only_current_tenant_courses(client):
    tenant_a_courses = client.get("/api/v1/courses", headers=auth_headers(client, "teacher-a@example.com", "tenant-a"))
    assert tenant_a_courses.status_code == 200
    assert {item["title"] for item in tenant_a_courses.json()} == {"Cyber Hygiene"}

    tenant_b_courses = client.get("/api/v1/courses", headers=auth_headers(client, "teacher-b@example.com", "tenant-b"))
    assert tenant_b_courses.status_code == 200
    assert {item["title"] for item in tenant_b_courses.json()} == {"Service workflow"}


def test_tenant_select_rejects_unrelated_tenant(client):
    response = client.post(
        "/api/v1/tenants/select",
        headers=auth_headers(client, "learner-a@example.com", "tenant-a"),
        json={"code": "tenant-b"},
    )
    assert response.status_code == 403


def test_teacher_cannot_create_test_for_foreign_tenant_course(client):
    foreign_courses = client.get("/api/v1/courses", headers=auth_headers(client, "teacher-b@example.com", "tenant-b"))
    assert foreign_courses.status_code == 200
    foreign_course_id = foreign_courses.json()[0]["id"]

    response = client.post(
        "/api/v1/tests",
        headers=auth_headers(client, "teacher-a@example.com", "tenant-a"),
        json={"course_id": foreign_course_id, "title": "Cross-tenant test", "baseline_difficulty": 3, "question_limit": 5},
    )
    assert response.status_code == 404


def test_teacher_cannot_create_lesson_for_foreign_tenant_course(client):
    foreign_courses = client.get("/api/v1/courses", headers=auth_headers(client, "teacher-b@example.com", "tenant-b"))
    assert foreign_courses.status_code == 200
    foreign_course_id = foreign_courses.json()[0]["id"]

    response = client.post(
        "/api/v1/lessons",
        headers=auth_headers(client, "teacher-a@example.com", "tenant-a"),
        json={
            "course_id": foreign_course_id,
            "topic_id": 1,
            "title": "Cross-tenant lesson",
            "summary": "",
            "content": "Blocked",
            "content_pages": [],
            "duration_minutes": 5,
            "sort_order": 1,
        },
    )
    assert response.status_code == 404


def test_teacher_cannot_assign_foreign_tenant_user(client):
    users_b = client.get("/api/v1/users", headers=auth_headers(client, "teacher-b@example.com", "tenant-b"))
    assert users_b.status_code == 200
    foreign_learner_id = next(item["id"] for item in users_b.json() if item["email"] == "learner-b@example.com")

    response = client.post(
        "/api/v1/courses/1/assign",
        headers=auth_headers(client, "teacher-a@example.com", "tenant-a"),
        json={"user_id": foreign_learner_id},
    )
    assert response.status_code == 422

from app.core.db import SessionLocal
from app.models.models import Group, GroupMember, User

from .conftest import auth_headers


def test_learner_can_upload_submission_file(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created_assignment = client.post(
        "/api/v1/assignments",
        headers=teacher_headers,
        json={
            "course_id": 1,
            "lesson_id": 1,
            "title": "Upload-enabled practical",
            "description": "Attach a document",
            "is_active": True,
        },
    )
    assert created_assignment.status_code == 200
    assignment_id = created_assignment.json()["id"]

    upload_response = client.post(
        "/api/v1/assignments/submissions/upload",
        headers=learner_headers,
        data={"assignment_id": assignment_id},
        files={"file": ("evidence.txt", b"submission evidence", "text/plain")},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["file_url"].startswith("/media/")
    assert payload["file_name"] == "evidence.txt"


def test_learner_can_submit_assignment_and_teacher_can_review(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created_assignment = client.post(
        "/api/v1/assignments",
        headers=teacher_headers,
        json={
            "course_id": 1,
            "lesson_id": 1,
            "title": "Practical check",
            "description": "Submit your implementation summary",
            "is_active": True,
        },
    )
    assert created_assignment.status_code == 200
    assignment_id = created_assignment.json()["id"]

    submission_response = client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=learner_headers,
        json={
            "status": "submitted",
            "text_answer": "Implemented and validated locally.",
            "link_answer": "https://example.com/work",
            "file_urls": ["/media/submission-proof.txt"],
        },
    )
    assert submission_response.status_code == 200
    submission = submission_response.json()
    assert submission["status"] == "submitted"
    assert submission["text_answer"] == "Implemented and validated locally."
    assert len(submission["files"]) == 1

    review_response = client.post(
        f"/api/v1/submissions/{submission['id']}/review",
        headers=teacher_headers,
        json={"status": "approved", "comment": "Good work"},
    )
    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["status"] == "approved"
    assert reviewed["latest_review"]["status"] == "approved"


def test_cross_tenant_assignment_access_is_blocked(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    learner_other_tenant_headers = auth_headers(client, "learner-b@example.com", "tenant-b")

    created_assignment = client.post(
        "/api/v1/assignments",
        headers=teacher_headers,
        json={
            "course_id": 1,
            "lesson_id": 1,
            "title": "Tenant-bound practical",
            "description": "Only tenant A should access this",
            "is_active": True,
        },
    )
    assert created_assignment.status_code == 200
    assignment_id = created_assignment.json()["id"]

    list_response = client.get(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=learner_other_tenant_headers,
    )
    assert list_response.status_code in {403, 404}

    submit_response = client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=learner_other_tenant_headers,
        json={"status": "submitted", "text_answer": "Cross-tenant attempt"},
    )
    assert submit_response.status_code in {403, 404}


def test_review_persists_grade_and_validates_range(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created_assignment = client.post(
        "/api/v1/assignments",
        headers=teacher_headers,
        json={
            "course_id": 1,
            "lesson_id": 1,
            "title": "Graded practical",
            "description": "Reviewer should grade the work",
            "is_active": True,
        },
    )
    assert created_assignment.status_code == 200
    assignment_id = created_assignment.json()["id"]

    submission_response = client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=learner_headers,
        json={
            "status": "submitted",
            "text_answer": "Готовая работа",
            "link_answer": "https://example.com/work",
            "file_urls": ["/media/proof.txt"],
        },
    )
    assert submission_response.status_code == 200
    submission_id = submission_response.json()["id"]

    graded_review = client.post(
        f"/api/v1/submissions/{submission_id}/review",
        headers=teacher_headers,
        json={"status": "approved", "comment": "Отлично", "grade": 85},
    )
    assert graded_review.status_code == 200
    payload = graded_review.json()
    assert payload["status"] == "approved"
    assert payload["latest_review"]["grade"] == 85
    assert payload["latest_review"]["comment"] == "Отлично"

    listed = client.get(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=teacher_headers,
    )
    assert listed.status_code == 200
    items = listed.json()
    assert items
    assert items[0]["latest_review"]["grade"] == 85

    out_of_range = client.post(
        f"/api/v1/submissions/{submission_id}/review",
        headers=teacher_headers,
        json={"status": "approved", "comment": "Too high", "grade": 150},
    )
    assert out_of_range.status_code == 422

    review_without_grade = client.post(
        f"/api/v1/submissions/{submission_id}/review",
        headers=teacher_headers,
        json={"status": "needs_revision", "comment": "Доработай"},
    )
    assert review_without_grade.status_code == 200
    assert review_without_grade.json()["latest_review"]["grade"] is None


def test_learner_cannot_review_submission(client):
    teacher_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created_assignment = client.post(
        "/api/v1/assignments",
        headers=teacher_headers,
        json={
            "course_id": 1,
            "lesson_id": 1,
            "title": "Review permissions check",
            "description": "Only staff can review",
            "is_active": True,
        },
    )
    assignment_id = created_assignment.json()["id"]

    submission = client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=learner_headers,
        json={"status": "submitted", "text_answer": "Needs review"},
    ).json()

    response = client.post(
        f"/api/v1/submissions/{submission['id']}/review",
        headers=learner_headers,
        json={"status": "approved", "comment": "Self-approve"},
    )
    assert response.status_code == 403


def test_list_course_assignments_returns_only_for_tenant(client):
    teacher_a_headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    teacher_b_headers = auth_headers(client, "teacher-b@example.com", "tenant-b")

    users_a = client.get("/api/v1/users", headers=teacher_a_headers).json()
    learner_a_id = next(item["id"] for item in users_a if item["email"] == "learner-a@example.com")
    users_b = client.get("/api/v1/users", headers=teacher_b_headers).json()
    learner_b_id = next(item["id"] for item in users_b if item["email"] == "learner-b@example.com")

    assigned_a = client.post("/api/v1/courses/1/assign", headers=teacher_a_headers, json={"user_id": learner_a_id})
    assert assigned_a.status_code == 200
    assigned_b = client.post("/api/v1/courses/2/assign", headers=teacher_b_headers, json={"user_id": learner_b_id})
    assert assigned_b.status_code == 200

    response = client.get("/api/v1/courses/1/assignments", headers=teacher_a_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert {item["user_id"] for item in payload} == {learner_a_id}
    assert all(item["effective_user_ids"] == [learner_a_id] for item in payload)


def test_delete_course_assignment_revokes_access(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")

    created = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"title": "Revocable course", "description": "Temporary access", "status": "published"},
    )
    assert created.status_code == 200
    course_id = created.json()["id"]
    learner_id = next(item["id"] for item in client.get("/api/v1/users", headers=admin_headers).json() if item["email"] == "learner-a@example.com")

    assigned = client.post(f"/api/v1/courses/{course_id}/assign", headers=admin_headers, json={"user_id": learner_id})
    assert assigned.status_code == 200
    learner_courses = client.get("/api/v1/courses", headers=learner_headers)
    assert any(item["id"] == course_id for item in learner_courses.json())

    assignments = client.get(f"/api/v1/courses/{course_id}/assignments", headers=admin_headers).json()
    response = client.delete(f"/api/v1/courses/{course_id}/assignments/{assignments[0]['id']}", headers=admin_headers)

    assert response.status_code == 204
    learner_courses_after_delete = client.get("/api/v1/courses", headers=learner_headers)
    assert all(item["id"] != course_id for item in learner_courses_after_delete.json())


def test_delete_course_assignment_404_when_other_course(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    learner_id = next(item["id"] for item in client.get("/api/v1/users", headers=admin_headers).json() if item["email"] == "learner-a@example.com")
    second_course = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"title": "Second revocation target", "description": "", "status": "published"},
    )
    assert second_course.status_code == 200
    assigned = client.post("/api/v1/courses/1/assign", headers=admin_headers, json={"user_id": learner_id})
    assert assigned.status_code == 200
    assignment_id = client.get("/api/v1/courses/1/assignments", headers=admin_headers).json()[0]["id"]

    response = client.delete(
        f"/api/v1/courses/{second_course.json()['id']}/assignments/{assignment_id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_delete_course_assignment_forbidden_for_learner(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    learner_id = next(item["id"] for item in client.get("/api/v1/users", headers=admin_headers).json() if item["email"] == "learner-a@example.com")
    assigned = client.post("/api/v1/courses/1/assign", headers=admin_headers, json={"user_id": learner_id})
    assert assigned.status_code == 200
    assignment_id = client.get("/api/v1/courses/1/assignments", headers=admin_headers).json()[0]["id"]

    response = client.delete(f"/api/v1/courses/1/assignments/{assignment_id}", headers=learner_headers)

    assert response.status_code == 403


def test_list_groups_returns_only_current_tenant(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    teacher_b_headers = auth_headers(client, "teacher-b@example.com", "tenant-b")
    db = SessionLocal()
    try:
        learner_a = db.query(User).filter(User.email == "learner-a@example.com").one()
        learner_b = db.query(User).filter(User.email == "learner-b@example.com").one()
        group_a = Group(tenant_id=1, name="Tenant A cohort")
        group_b = Group(tenant_id=2, name="Tenant B cohort")
        db.add_all([group_a, group_b])
        db.flush()
        db.add_all(
            [
                GroupMember(tenant_id=1, group_id=group_a.id, user_id=learner_a.id),
                GroupMember(tenant_id=2, group_id=group_b.id, user_id=learner_b.id),
            ]
        )
        db.commit()
    finally:
        db.close()

    response_a = client.get("/api/v1/groups", headers=admin_headers)
    response_b = client.get("/api/v1/groups", headers=teacher_b_headers)

    assert response_a.status_code == 200
    assert response_a.json() == [{"id": 1, "name": "Tenant A cohort", "member_count": 1}]
    assert response_b.status_code == 200
    assert response_b.json() == [{"id": 2, "name": "Tenant B cohort", "member_count": 1}]


def test_create_group_creates_tenant_scoped_group(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    create_response = client.post("/api/v1/groups", headers=admin_headers, json={"name": "New cohort"})
    assert create_response.status_code == 200
    assert create_response.json()["name"] == "New cohort"
    listed = client.get("/api/v1/groups", headers=admin_headers)
    assert listed.status_code == 200
    assert any(group["name"] == "New cohort" for group in listed.json())


def test_group_member_add_list_remove_flow(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    users = client.get("/api/v1/users", headers=admin_headers).json()
    learner_id = next(item["id"] for item in users if item["email"] == "learner-a@example.com")
    created_group = client.post("/api/v1/groups", headers=admin_headers, json={"name": "Flow group"})
    assert created_group.status_code == 200
    group_id = created_group.json()["id"]

    add_response = client.post(f"/api/v1/groups/{group_id}/members", headers=admin_headers, json={"user_id": learner_id})
    assert add_response.status_code == 200
    assert add_response.json()["user_id"] == learner_id

    members_response = client.get(f"/api/v1/groups/{group_id}/members", headers=admin_headers)
    assert members_response.status_code == 200
    assert [item["user_id"] for item in members_response.json()] == [learner_id]

    remove_response = client.delete(f"/api/v1/groups/{group_id}/members/{learner_id}", headers=admin_headers)
    assert remove_response.status_code == 200
    assert remove_response.json()["deleted"] is True

    members_after = client.get(f"/api/v1/groups/{group_id}/members", headers=admin_headers)
    assert members_after.status_code == 200
    assert members_after.json() == []


def test_group_member_add_forbidden_for_learner(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    users = client.get("/api/v1/users", headers=admin_headers).json()
    teacher_id = next(item["id"] for item in users if item["email"] == "teacher-a@example.com")
    created_group = client.post("/api/v1/groups", headers=admin_headers, json={"name": "Security group"})
    assert created_group.status_code == 200
    group_id = created_group.json()["id"]

    add_response = client.post(f"/api/v1/groups/{group_id}/members", headers=learner_headers, json={"user_id": teacher_id})
    assert add_response.status_code == 403

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

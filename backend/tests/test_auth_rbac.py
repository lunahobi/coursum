from datetime import UTC, datetime, timedelta

import jwt

from app.core.rate_limit import auth_rate_limiter
from app.core.security import create_token

from .conftest import auth_headers


def test_teacher_can_list_users(client):
    response = client.get("/api/v1/users", headers=auth_headers(client, "teacher-a@example.com", "tenant-a"))
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_system_admin_membership_hidden_in_tenant_user_list(client):
    response = client.get("/api/v1/users", headers=auth_headers(client, "admin-a@example.com", "tenant-a"))
    assert response.status_code == 200
    emails = {user["email"] for user in response.json()}
    assert "sysadmin-a@example.com" not in emails


def test_learner_cannot_list_users(client):
    response = client.get("/api/v1/users", headers=auth_headers(client, "learner-a@example.com", "tenant-a"))
    assert response.status_code == 403


def test_learner_cannot_access_web_panel_admin_endpoints(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    checks = [
        ("get", "/api/v1/analytics/dashboard", None),
        ("get", "/api/v1/media/library", None),
        ("post", "/api/v1/courses", {"title": "Blocked", "description": "", "image_url": None}),
        ("patch", "/api/v1/courses/1", {"title": "Blocked", "description": "", "image_url": None}),
        ("delete", "/api/v1/courses/1", None),
        (
            "post",
            "/api/v1/lessons",
            {
                "course_id": 1,
                "topic_id": 1,
                "title": "Blocked lesson",
                "summary": "",
                "content": "Blocked",
                "content_pages": [],
                "duration_minutes": 5,
                "sort_order": 1,
            },
        ),
        ("patch", "/api/v1/lessons/1", {"course_id": 1, "topic_id": 1, "title": "Blocked", "summary": "", "content": "Blocked", "content_pages": [], "duration_minutes": 5, "sort_order": 1}),
        ("post", "/api/v1/tests", {"course_id": 1, "title": "Blocked test", "baseline_difficulty": 3, "question_limit": 5}),
        (
            "post",
            "/api/v1/questions",
            {
                "test_id": 1,
                "text": "Blocked question",
                "difficulty": 3,
                "estimated_seconds": 30,
                "topic_ids": [1],
                "options": [
                    {"text": "Yes", "is_correct": True},
                    {"text": "No", "is_correct": False},
                ],
            },
        ),
        (
            "patch",
            "/api/v1/questions/1",
            {
                "test_id": 1,
                "text": "Blocked question update",
                "difficulty": 3,
                "estimated_seconds": 30,
                "topic_ids": [1],
                "options": [
                    {"text": "Yes", "is_correct": True},
                    {"text": "No", "is_correct": False},
                ],
            },
        ),
        ("post", "/api/v1/courses/1/assign", {"user_id": 3}),
        ("post", "/api/v1/users", {"email": "blocked@example.com", "full_name": "Blocked", "password": "Password123!", "role_name": "learner"}),
        ("patch", "/api/v1/users/1", {"full_name": "Blocked user"}),
    ]
    for method, path, payload in checks:
        request = getattr(client, method)
        response = request(path, headers=headers, json=payload) if payload is not None else request(path, headers=headers)
        assert response.status_code == 403, f"{method.upper()} {path} should be forbidden for learners"


def test_org_admin_cannot_grant_system_admin_role(client):
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(client, "admin-a@example.com", "tenant-a"),
        json={
            "email": "forbidden-sysadmin@example.com",
            "full_name": "Forbidden SysAdmin",
            "password": "Password123!",
            "role_name": "system_admin",
        },
    )
    assert response.status_code == 403


def test_auth_me_includes_current_tenant_role(client):
    response = client.get("/api/v1/auth/me", headers=auth_headers(client, "teacher-a@example.com", "tenant-a"))
    assert response.status_code == 200
    assert response.json()["tenant_role"] == "teacher"


def test_auth_me_without_tenant_context_still_returns_profile(client):
    token = client.post("/api/v1/auth/login", json={"email": "teacher-a@example.com", "password": "Password123!"}).json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}", "Host": "localhost"})
    assert response.status_code == 200
    assert response.json()["tenant_role"] is None


def test_expired_access_token_returns_401(client):
    expired_token = jwt.encode(
        {
            "sub": "2",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "jti": "expired-token-test",
        },
        "change-me-in-production",
        algorithm="HS256",
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}", "X-Tenant-Code": "tenant-a", "Host": "localhost"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Access token expired"


def test_tokens_are_unique_even_for_same_user_and_type():
    first = create_token("1", "refresh", 60)
    second = create_token("1", "refresh", 60)
    assert first != second


def test_deactivated_user_cannot_login(client):
    admin_headers = auth_headers(client, "admin-a@example.com", "tenant-a")
    users = client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 200
    learner = next((item for item in users.json() if item["email"] == "learner-a@example.com"), None)
    assert learner is not None

    deactivate = client.patch(
        f"/api/v1/users/{learner['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivate.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "learner-a@example.com", "password": "Password123!"},
    )
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "User is deactivated"


def test_login_rate_limit_returns_429(client):
    old_limit = auth_rate_limiter.limit
    old_window = auth_rate_limiter.window_seconds
    auth_rate_limiter.limit = 2
    auth_rate_limiter.window_seconds = 60

    try:
        first = client.post("/api/v1/auth/login", json={"email": "teacher-a@example.com", "password": "Password123!"})
        second = client.post("/api/v1/auth/login", json={"email": "teacher-a@example.com", "password": "Password123!"})
        third = client.post("/api/v1/auth/login", json={"email": "teacher-a@example.com", "password": "Password123!"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
    finally:
        auth_rate_limiter.limit = old_limit
        auth_rate_limiter.window_seconds = old_window


def test_db_health_endpoint(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analytics_timeline_endpoint_returns_series(client):
    response = client.get(
        "/api/v1/analytics/timeline?period=7d",
        headers=auth_headers(client, "teacher-a@example.com", "tenant-a"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"labels", "attempts", "completions"}
    assert len(payload["labels"]) == 7
    assert len(payload["attempts"]) == 7
    assert len(payload["completions"]) == 7


def test_analytics_timeline_rejects_invalid_period(client):
    response = client.get(
        "/api/v1/analytics/timeline?period=bad",
        headers=auth_headers(client, "teacher-a@example.com", "tenant-a"),
    )
    assert response.status_code == 422

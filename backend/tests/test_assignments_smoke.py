from .conftest import auth_headers


def test_assignments_endpoint_is_reachable_for_learner(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    response = client.get("/api/v1/assignments", headers=headers)
    assert response.status_code == 200

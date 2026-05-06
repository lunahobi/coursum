from .conftest import auth_headers


def test_question_list_includes_editing_payload_and_patch_updates_question(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    listed = client.get("/api/v1/questions?test_id=1", headers=headers)
    assert listed.status_code == 200
    questions = listed.json()
    assert questions
    first_question = questions[0]
    assert first_question["options"]
    assert first_question["topic_ids"] == [1]

    updated = client.patch(
        f"/api/v1/questions/{first_question['id']}",
        headers=headers,
        json={
            "test_id": 1,
            "text": "Should you acknowledge the customer's issue first?",
            "explanation": "Lead with empathy, then clarify.",
            "difficulty": 4,
            "estimated_seconds": 50,
            "topic_ids": [1],
            "options": [
                {"text": "Yes, acknowledge and clarify", "is_correct": True},
                {"text": "No, correct them immediately", "is_correct": False},
            ],
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["text"] == "Should you acknowledge the customer's issue first?"
    assert payload["difficulty"] == 4
    assert payload["estimated_seconds"] == 50
    assert payload["topic_ids"] == [1]
    assert payload["options"] == [
        {"id": payload["options"][0]["id"], "text": "Yes, acknowledge and clarify", "is_correct": True},
        {"id": payload["options"][1]["id"], "text": "No, correct them immediately", "is_correct": False},
    ]

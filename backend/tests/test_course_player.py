import copy

from app.api.routes import media as media_routes
from app.core.db import SessionLocal
from app.models.models import Lesson
from app.services import lesson_player

from .conftest import auth_headers


def test_learner_can_fetch_course_outline_with_current_position(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    response = client.get("/api/v1/courses/1/outline", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == 1
    assert payload["resume_lesson_id"] == 1
    assert payload["sections"] == []
    assert len(payload["lessons"]) == 2
    assert payload["lessons"][0]["section_id"] is None
    assert payload["lessons"][0]["is_current"] is True
    assert payload["lessons"][0]["page_count"] == 2


def test_lesson_state_persists_and_recalculates_progress(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    first = client.post(
        "/api/v1/lessons/1/state",
        headers=headers,
        json={"current_page_index": 1, "completed_page_ids": ["passwords-overview", "passwords-practice"], "is_completed": True},
    )
    assert first.status_code == 200
    assert first.json()["progress_percent"] == 50

    player = client.get("/api/v1/lessons/1/player", headers=headers)
    assert player.status_code == 200
    player_payload = player.json()
    assert player_payload["state"]["current_page_index"] == 1
    assert player_payload["state"]["is_completed"] is True
    assert player_payload["next_lesson_id"] == 2

    second = client.post("/api/v1/lessons/2/progress", headers=headers)
    assert second.status_code == 200
    assert second.json()["progress_percent"] == 100
    assert second.json()["course_completed"] is True


def test_invalid_video_sources_are_rejected_on_lesson_create(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    response = client.post(
        "/api/v1/lessons",
        headers=headers,
        json={
            "course_id": 1,
            "title": "Unsafe video",
            "summary": "Should fail",
            "content": "legacy",
            "content_pages": [
                {
                    "chapter_title": "Unsafe",
                    "page_title": "Bad embed",
                    "blocks": [{"type": "video", "url": "https://youtube.com/watch?v=abc"}],
                }
            ],
            "sort_order": 3,
        },
    )
    assert response.status_code == 422
    assert "MP4" in response.json()["detail"]


def test_html_blocks_are_sanitized_and_preserved_in_player(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    create = client.post(
        "/api/v1/lessons",
        headers=headers,
        json={
            "course_id": 1,
            "title": "HTML lesson",
            "summary": "Rich lesson body",
            "content": "legacy",
            "content_pages": [
                {
                    "chapter_title": "Rich text",
                    "page_title": "HTML page",
                    "blocks": [
                        {
                            "type": "html",
                            "html": "<h2>Checklist</h2><p>Use the <strong>approved</strong> flow.</p><script>alert('x')</script>",
                        }
                    ],
                }
            ],
            "sort_order": 3,
        },
    )
    assert create.status_code == 200
    lesson_id = create.json()["id"]

    learner_headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    player = client.get(f"/api/v1/lessons/{lesson_id}/player", headers=learner_headers)
    assert player.status_code == 200
    payload = player.json()
    html_block = payload["pages"][0]["blocks"][0]
    assert html_block["type"] == "html"
    assert "<h2>Checklist</h2>" in html_block["html"]
    assert "<script" not in html_block["html"]


def test_teacher_can_update_lesson_with_html_blocks(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    response = client.patch(
        "/api/v1/lessons/1",
        headers=headers,
        json={
            "course_id": 1,
            "topic_id": 1,
            "title": "Password manager basics updated",
            "summary": "Updated summary",
            "content": "legacy fallback",
            "content_pages": [
                {
                    "chapter_title": "Rich text",
                    "page_title": "Updated HTML page",
                    "blocks": [
                        {"type": "html", "html": "<h2>Updated</h2><p>Safer sign-in flow.</p>"},
                        {"type": "image", "url": "/media/onboarding-cover-ru.png", "alt": "cover"},
                    ],
                }
            ],
            "duration_minutes": 10,
            "image_url": "/media/onboarding-cover-ru.png",
            "video_url": "https://cdn.example.com/passwords.mp4",
            "sort_order": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Password manager basics updated"
    assert payload["content_pages"][0]["blocks"][0]["html"].startswith("<h2>Updated</h2>")


def test_invalid_video_inside_html_block_is_rejected(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    response = client.post(
        "/api/v1/lessons",
        headers=headers,
        json={
            "course_id": 1,
            "title": "Unsafe html video",
            "summary": "Should fail",
            "content": "legacy",
            "content_pages": [
                {
                    "chapter_title": "Unsafe",
                    "page_title": "HTML media",
                    "blocks": [
                        {"type": "html", "html": "<video controls src='https://youtube.com/watch?v=abc'></video>"}
                    ],
                }
            ],
            "sort_order": 3,
        },
    )
    assert response.status_code == 422
    assert "MP4" in response.json()["detail"]


def test_player_falls_back_to_lesson_video_when_page_video_is_missing(client, tmp_path, monkeypatch):
    monkeypatch.setattr(lesson_player, "_media_root", lambda: tmp_path)
    (tmp_path / "fallback.mp4").write_bytes(b"video")

    db = SessionLocal()
    lesson = db.get(Lesson, 1)
    assert lesson is not None
    lesson.video_url = "/media/fallback.mp4"
    content_pages = copy.deepcopy(lesson.content_pages or [])
    content_pages[0]["blocks"][1]["url"] = "/media/missing.mp4"
    lesson.content_pages = content_pages
    db.add(lesson)
    db.commit()
    db.close()

    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    response = client.get("/api/v1/lessons/1/player", headers=headers)
    assert response.status_code == 200
    video_block = response.json()["pages"][0]["blocks"][1]
    assert video_block["url"] == "/media/fallback.mp4"
    assert video_block["status"] == "ready"
    assert video_block["error"] is None


def test_media_library_lists_local_assets(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    response = client.get("/api/v1/media/library", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


def test_teacher_can_upload_image_and_see_it_in_media_library(client, tmp_path, monkeypatch):
    monkeypatch.setattr(media_routes, "get_media_root", lambda tenant: (tmp_path, f"/media/{tenant.code}"))
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    upload = client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("lesson-diagram.png", b"fake-png-binary", "image/png")},
        data={"target_kind": "image"},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["kind"] == "image"
    assert payload["path"].startswith("/media/tenant-a/lesson-diagram-")
    assert payload["filename"].endswith(".png")
    assert payload["mime_type"] == "image/png"

    library = client.get("/api/v1/media/library", headers=headers)
    assert library.status_code == 200
    assets = library.json()
    assert any(item["filename"] == payload["filename"] for item in assets)


def test_teacher_can_upload_video_and_see_it_in_media_library(client, tmp_path, monkeypatch):
    monkeypatch.setattr(media_routes, "get_media_root", lambda tenant: (tmp_path, f"/media/{tenant.code}"))
    monkeypatch.setattr(media_routes, "_transcode_video", lambda source, destination: destination.write_bytes(b"normalized-video"))
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    upload = client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("lesson-walkthrough.mov", b"fake-mov-binary", "video/quicktime")},
        data={"target_kind": "video"},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["kind"] == "video"
    assert payload["path"].startswith("/media/tenant-a/lesson-walkthrough-")
    assert payload["filename"].endswith(".mp4")
    assert payload["mime_type"] == "video/mp4"

    library = client.get("/api/v1/media/library", headers=headers)
    assert library.status_code == 200
    assets = library.json()
    assert any(item["filename"] == payload["filename"] for item in assets)


def test_teacher_can_upload_document_and_insert_it_in_lesson_html(client, tmp_path, monkeypatch):
    monkeypatch.setattr(media_routes, "get_media_root", lambda tenant: (tmp_path, f"/media/{tenant.code}"))
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    upload = client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("lesson-notes.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"target_kind": "document"},
    )
    assert upload.status_code == 200
    asset = upload.json()
    assert asset["kind"] == "document"
    assert asset["path"].startswith("/media/tenant-a/lesson-notes-")
    assert asset["filename"].endswith(".pdf")
    assert asset["mime_type"] == "application/pdf"

    response = client.post(
        "/api/v1/lessons",
        headers=headers,
        json={
            "course_id": 1,
            "title": "Lesson with notes",
            "summary": "Read the attached notes.",
            "content": "legacy",
            "content_pages": [
                {
                    "chapter_title": "Notes",
                    "page_title": "Download",
                    "blocks": [
                        {
                            "type": "html",
                            "html": f'<p><a href="{asset["path"]}" target="_blank" rel="noopener noreferrer">Lesson notes</a></p>',
                        }
                    ],
                }
            ],
            "sort_order": 9,
        },
    )
    assert response.status_code == 200
    html = response.json()["content_pages"][0]["blocks"][0]["html"]
    assert asset["path"] in html
    assert "Lesson notes" in html


def test_upload_rejects_mismatched_media_kind(client, tmp_path, monkeypatch):
    monkeypatch.setattr(media_routes, "get_media_root", lambda tenant: (tmp_path, f"/media/{tenant.code}"))
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    response = client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("clip.mp4", b"fake-video-binary", "video/mp4")},
        data={"target_kind": "image"},
    )
    assert response.status_code == 422
    assert "Unsupported image content type" in response.json()["detail"]


def test_upload_rejects_svg_for_mobile_compatible_images(client, tmp_path, monkeypatch):
    monkeypatch.setattr(media_routes, "get_media_root", lambda tenant: (tmp_path, f"/media/{tenant.code}"))
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")

    response = client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("diagram.svg", b"<svg></svg>", "image/svg+xml")},
        data={"target_kind": "image"},
    )
    assert response.status_code == 422
    assert "Unsupported image content type" in response.json()["detail"]


def test_cross_tenant_player_access_is_denied(client):
    headers = auth_headers(client, "learner-b@example.com", "tenant-b")
    response = client.get("/api/v1/lessons/1/player", headers=headers)
    assert response.status_code == 404


def test_legacy_lessons_still_render_in_player(client):
    headers = auth_headers(client, "learner-a@example.com", "tenant-a")
    response = client.get("/api/v1/lessons/2/player", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["lesson_id"] == 2
    assert len(payload["pages"]) >= 1
    assert payload["pages"][0]["page_title"]


def test_teacher_can_update_course_metadata(client):
    headers = auth_headers(client, "teacher-a@example.com", "tenant-a")
    response = client.patch(
        "/api/v1/courses/1",
        headers=headers,
        json={"title": "Updated course title", "description": "Updated description"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Updated course title"
    assert payload["description"] == "Updated description"

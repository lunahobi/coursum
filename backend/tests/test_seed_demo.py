from dataclasses import fields, is_dataclass
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.text_repair import repair_mojibake_text
from scripts.seed_demo import build_course_catalog_ru, localized_cover_path


def _walk_strings(value):
    if isinstance(value, str):
        yield value
        return
    if is_dataclass(value):
        for field in fields(value):
            yield from _walk_strings(getattr(value, field.name))
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def test_repair_mojibake_text_restores_russian_text():
    broken = "\u0420\u2019\u0421\u2039 \u0420\u0457\u0420\u0455\u0420\u0405\u0420\u0451\u0420\u0458\u0420\xb0\u0420\xb5\u0421\u201a\u0420\xb5 \u0421\u0402\u0420\xb0\u0420\xb7\u0420\u0405\u0420\u0451\u0421\u2020\u0421\u0453 \u0420\u0458\u0420\xb5\u0420\xb6\u0420\u0491\u0421\u0453 \u0420\u0405\u0420\xb0\u0421\u0403\u0421\u201a\u0420\xb0\u0420\u0406\u0420\u0405\u0420\u0451\u0420\u0454\u0420\u0455\u0420\u0458 \u0420\u0451 \u0421\u0402\u0421\u0453\u0420\u0454\u0420\u0455\u0420\u0406\u0420\u0455\u0420\u0491\u0420\u0451\u0421\u201a\u0420\xb5\u0420\xbb\u0420\xb5\u0420\u0458."
    assert repair_mojibake_text(broken) == "\u0412\u044b \u043f\u043e\u043d\u0438\u043c\u0430\u0435\u0442\u0435 \u0440\u0430\u0437\u043d\u0438\u0446\u0443 \u043c\u0435\u0436\u0434\u0443 \u043d\u0430\u0441\u0442\u0430\u0432\u043d\u0438\u043a\u043e\u043c \u0438 \u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u0435\u043c."


def test_russian_catalog_is_seeded_with_readable_titles_and_pages():
    catalog = build_course_catalog_ru()
    first_course = catalog[0]
    first_lesson = first_course.lessons[0]

    assert first_course.title == "\u041a\u043e\u0440\u043f\u043e\u0440\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u043e\u043d\u0431\u043e\u0440\u0434\u0438\u043d\u0433 \u0438 \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0435 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u044b"
    assert first_lesson.title == "\u041a\u0442\u043e \u0437\u0430 \u0447\u0442\u043e \u043e\u0442\u0432\u0435\u0447\u0430\u0435\u0442 \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438"
    assert first_lesson.content.startswith("## \u0426\u0435\u043b\u044c \u0443\u0440\u043e\u043a\u0430")
    assert first_lesson.content_pages[0]["chapter_title"] == "\u041a\u043e\u043d\u0442\u0435\u043a\u0441\u0442"
    assert first_lesson.content_pages[0]["page_title"] == "\u041a\u0442\u043e \u0441\u043d\u0438\u043c\u0430\u0435\u0442 \u043a\u0430\u043a\u043e\u0439 \u0431\u043b\u043e\u043a\u0435\u0440"
    assert len(first_lesson.content_pages) >= 5
    assert "\u0422\u0438\u043f\u0438\u0447\u043d\u044b\u0435 \u043e\u0448\u0438\u0431\u043a\u0438" in first_lesson.content


def test_russian_catalog_has_richer_question_banks():
    catalog = build_course_catalog_ru()
    assert all(len(course.questions) >= 16 for course in catalog)
    assert catalog[0].questions[-1].difficulty >= 4


def test_russian_catalog_uses_lesson_specific_page_copy():
    lesson = build_course_catalog_ru()[0].lessons[0]
    signals_html = lesson.content_pages[1]["blocks"][0]["html"]
    pitfalls_html = lesson.content_pages[3]["blocks"][0]["html"]
    assert "\u0442\u0440\u0438\u0434\u0446\u0430\u0442\u044c \u0441\u0435\u043a\u0443\u043d\u0434" in signals_html
    assert "\u041f\u0438\u0441\u0430\u0442\u044c \u0432 \u043e\u0431\u0449\u0438\u0439 \u0447\u0430\u0442" in pitfalls_html
    assert "\u041d\u0435 \u043a \u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044e \u0438\u0434\u0443\u0442" not in pitfalls_html


def test_russian_catalog_differentiates_same_topic_lessons():
    lessons = build_course_catalog_ru()[1].lessons
    password_hygiene = lessons[0]
    password_reuse = lessons[1]
    assert password_hygiene.content_pages[0]["page_title"] == "\u041a\u0430\u043a\u0438\u0435 \u043f\u0440\u0438\u0432\u044b\u0447\u043a\u0438 \u0440\u0435\u0430\u043b\u044c\u043d\u043e \u0437\u0430\u0449\u0438\u0449\u0430\u044e\u0442 \u0430\u043a\u043a\u0430\u0443\u043d\u0442"
    assert password_reuse.content_pages[0]["page_title"] == "\u041a\u0430\u043a \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f \u0443\u0442\u0435\u0447\u043a\u0430 \u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0441\u044f \u043a\u043e\u0440\u043f\u043e\u0440\u0430\u0442\u0438\u0432\u043d\u043e\u0439"
    hygiene_risks = password_hygiene.content_pages[3]["blocks"][0]["html"]
    reuse_risks = password_reuse.content_pages[3]["blocks"][0]["html"]
    assert "\u043f\u0440\u043e\u0441\u0438\u0442 \u043f\u0440\u0438\u0441\u043b\u0430\u0442\u044c" in password_hygiene.content_pages[2]["blocks"][0]["html"]
    assert "credential stuffing" in reuse_risks
    assert hygiene_risks != reuse_risks


def test_russian_catalog_does_not_duplicate_page_title_inside_html_heading():
    lesson = build_course_catalog_ru()[0].lessons[0]
    for page in lesson.content_pages:
        html = page["blocks"][0].get("html", "")
        assert f"<h2>{page['page_title']}</h2>" not in html


def test_localized_cover_path_supports_repaired_russian_titles():
    assert localized_cover_path("\u041a\u043e\u0440\u043f\u043e\u0440\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u043e\u043d\u0431\u043e\u0440\u0434\u0438\u043d\u0433 \u0438 \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0435 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u044b", "ru") == "/media/onboarding-cover-ru.png"
    assert localized_cover_path("\u041e\u0441\u043d\u043e\u0432\u044b \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u043e\u043d\u043d\u043e\u0439 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e\u0441\u0442\u0438 \u0434\u043b\u044f \u043e\u0444\u0438\u0441\u043d\u044b\u0445 \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432", "ru") == "/media/security-cover-ru.png"


def test_russian_catalog_contains_no_repairable_strings():
    catalog = build_course_catalog_ru()
    for item in _walk_strings(catalog):
        assert repair_mojibake_text(item) == item

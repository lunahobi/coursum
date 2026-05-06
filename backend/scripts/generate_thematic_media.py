from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


MEDIA_ROOT = Path(__file__).parent.parent / "app" / "static" / "media"
COURSE_COVER_SIZE = (1200, 675)
LESSON_IMAGE_SIZE = (1200, 675)
VIDEO_SIZE = (960, 540)
VIDEO_FPS = 24.0
VIDEO_DURATION_SECONDS = 5

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
]
REGULAR_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
]

THEMES = {
    "onboarding": {
        "start": "#1F5F8B",
        "end": "#4EA1D3",
        "panel": "#0F2236",
        "accent": "#CFE8FF",
    },
    "security": {
        "start": "#17324D",
        "end": "#2D6A8C",
        "panel": "#0E1B29",
        "accent": "#BDE9DA",
    },
    "service": {
        "start": "#6A3C1D",
        "end": "#C97A3D",
        "panel": "#2E1A0D",
        "accent": "#F7DFC7",
    },
}

COURSE_COVERS = [
    {
        "filename": "onboarding-cover-ru.png",
        "theme": "onboarding",
        "title": "Онбординг и внутренние процессы",
        "subtitle": "Роли, рабочие инструменты, коммуникация и уверенный старт в компании.",
    },
    {
        "filename": "security-cover-ru.png",
        "theme": "security",
        "title": "Основы информационной безопасности",
        "subtitle": "Пароли, фишинг, работа с данными и первые действия при инциденте.",
    },
    {
        "filename": "service-cover-ru.png",
        "theme": "service",
        "title": "Стандарты клиентского сервиса",
        "subtitle": "Владение запросом, жалобы, эмпатия и деэскалация.",
    },
    {
        "filename": "onboarding-cover-en.png",
        "theme": "onboarding",
        "title": "Onboarding and Internal Processes",
        "subtitle": "Roles, tools, communication, and confident first-week adaptation.",
    },
    {
        "filename": "security-cover-en.png",
        "theme": "security",
        "title": "Security Essentials",
        "subtitle": "Passwords, phishing, data handling, and first response to incidents.",
    },
    {
        "filename": "service-cover-en.png",
        "theme": "service",
        "title": "Client Service Standards",
        "subtitle": "Ownership, complaint handling, empathy, and de-escalation.",
    },
]

LESSON_MEDIA = [
    {
        "key": "onboarding-org-roles",
        "theme": "onboarding",
        "glyph": "org",
        "ru": {
            "title": "Кто за что отвечает в компании",
            "subtitle": "Куда идти с вопросами по HR, IT, безопасности и рабочим приоритетам.",
        },
        "en": {
            "title": "Who does what in the company",
            "subtitle": "Where HR, IT, security, and day-to-day ownership really sit.",
        },
    },
    {
        "key": "onboarding-portal",
        "theme": "onboarding",
        "glyph": "portal",
        "ru": {
            "title": "Как работать с корпоративным порталом",
            "subtitle": "Политики, формы, новости и база знаний в одном официальном месте.",
        },
        "en": {
            "title": "Working with the corporate portal",
            "subtitle": "Policies, forms, news, and knowledge-base links in one official source.",
        },
    },
    {
        "key": "onboarding-task-tracker",
        "theme": "onboarding",
        "glyph": "tracker",
        "ru": {
            "title": "Трекер задач и рабочий мессенджер",
            "subtitle": "Что держать в чате, а что сразу переводить в задачу с дедлайном.",
        },
        "en": {
            "title": "Task tracker and messenger basics",
            "subtitle": "What stays in chat and what must become a visible task with an owner.",
        },
    },
    {
        "key": "onboarding-business-message",
        "theme": "onboarding",
        "glyph": "message",
        "ru": {
            "title": "Как писать деловые сообщения",
            "subtitle": "Кратко, по делу и так, чтобы по сообщению можно было действовать.",
        },
        "en": {
            "title": "How to write business messages",
            "subtitle": "Keep requests short, specific, and easy to act on.",
        },
    },
    {
        "key": "onboarding-escalation",
        "theme": "onboarding",
        "glyph": "escalation",
        "ru": {
            "title": "Карта эскалации для нового сотрудника",
            "subtitle": "Кому писать, если блокер не решается и срок уже поджимает.",
        },
        "en": {
            "title": "Escalation map for a new employee",
            "subtitle": "Who to contact when a blocker stays unresolved and deadlines move closer.",
        },
    },
    {
        "key": "security-passwords",
        "theme": "security",
        "glyph": "lock",
        "ru": {
            "title": "Надежные пароли и MFA",
            "subtitle": "Как защитить доступ к рабочим системам без лишней рутины.",
        },
        "en": {
            "title": "Strong password policy",
            "subtitle": "How to protect access to business systems without adding needless friction.",
        },
    },
    {
        "key": "security-password-reuse",
        "theme": "security",
        "glyph": "reuse",
        "ru": {
            "title": "Почему опасно повторно использовать пароль",
            "subtitle": "Одна утечка может открыть цепочку доступов сразу в нескольких системах.",
        },
        "en": {
            "title": "Why password reuse is dangerous",
            "subtitle": "One leaked password can unlock a chain of business accounts.",
        },
    },
    {
        "key": "security-phishing",
        "theme": "security",
        "glyph": "phishing",
        "ru": {
            "title": "Как распознать фишинговое письмо",
            "subtitle": "Тревожные признаки в теме, отправителе, ссылках и формулировках срочности.",
        },
        "en": {
            "title": "How to spot phishing",
            "subtitle": "Warning signals in the sender, links, urgency cues, and request context.",
        },
    },
    {
        "key": "security-confidential-files",
        "theme": "security",
        "glyph": "files",
        "ru": {
            "title": "Работа с конфиденциальными файлами",
            "subtitle": "Где хранить документы, как делиться доступом и чего избегать.",
        },
        "en": {
            "title": "Working with confidential files",
            "subtitle": "Where files belong, how to share access, and what shortcuts are risky.",
        },
    },
    {
        "key": "security-incident-response",
        "theme": "security",
        "glyph": "incident",
        "ru": {
            "title": "Что делать при подозрении на компрометацию",
            "subtitle": "Остановить риск, сообщить вовремя и сохранить полезный контекст для ИБ.",
        },
        "en": {
            "title": "What to do after a suspected compromise",
            "subtitle": "Contain the risk, notify fast, and preserve useful context for security.",
        },
    },
    {
        "key": "service-request-ownership",
        "theme": "service",
        "glyph": "ownership",
        "ru": {
            "title": "Кто владеет запросом",
            "subtitle": "Показываем клиенту, что кейс под контролем и не потеряется между командами.",
        },
        "en": {
            "title": "Who owns the request",
            "subtitle": "Show the client that the case is owned and will not vanish between teams.",
        },
    },
    {
        "key": "service-empathy",
        "theme": "service",
        "glyph": "empathy",
        "ru": {
            "title": "Эмпатия без ложных обещаний",
            "subtitle": "Поддержать клиента, сохранив честные сроки и ясные ожидания.",
        },
        "en": {
            "title": "Empathy without false promises",
            "subtitle": "Support the client while keeping timelines and expectations honest.",
        },
    },
    {
        "key": "service-complaints",
        "theme": "service",
        "glyph": "complaint",
        "ru": {
            "title": "Структура обработки жалобы",
            "subtitle": "Принять, уточнить, зафиксировать план действий и вернуть доверие.",
        },
        "en": {
            "title": "Complaint handling structure",
            "subtitle": "Receive, clarify, document the plan, and rebuild confidence quickly.",
        },
    },
    {
        "key": "service-deescalation",
        "theme": "service",
        "glyph": "deescalation",
        "ru": {
            "title": "Как успокоить напряженного клиента",
            "subtitle": "Снизить эмоциональный градус и вернуть разговор к фактам и шагам.",
        },
        "en": {
            "title": "How to calm a tense client",
            "subtitle": "Lower the emotional pressure and bring the conversation back to action.",
        },
    },
    {
        "key": "service-overdue-escalation",
        "theme": "service",
        "glyph": "deadline",
        "ru": {
            "title": "Эскалация просроченных кейсов",
            "subtitle": "Когда поднимать уровень и как объяснять клиенту следующий шаг без хаоса.",
        },
        "en": {
            "title": "Escalating overdue cases",
            "subtitle": "When to raise the case and how to explain the next move without chaos.",
        },
    },
]


def load_font(size: int, *, bold: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = FONT_CANDIDATES if bold else REGULAR_FONT_CANDIDATES
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def gradient_background(size: tuple[int, int], start: str, end: str) -> Image.Image:
    width, height = size
    start_rgb = np.array(hex_to_rgb(start), dtype=np.float32)
    end_rgb = np.array(hex_to_rgb(end), dtype=np.float32)
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)
    blend = (np.outer(np.ones(height, dtype=np.float32), x) * 0.6) + (
        np.outer(y, np.ones(width, dtype=np.float32)) * 0.4
    )
    blend = np.clip(blend, 0.0, 1.0)[..., None]
    rgb = (start_rgb * (1.0 - blend) + end_rgb * blend).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_card_shell(image: Image.Image, theme: dict[str, str]) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    draw.ellipse((-160, height - 220, 280, height + 220), fill=(255, 255, 255, 38))
    draw.ellipse((width - 330, -140, width + 120, 220), fill=(255, 255, 255, 28))
    draw.rounded_rectangle(
        (64, 60, width - 64, height - 60),
        radius=38,
        fill=(15, 23, 34, 150),
        outline=(255, 255, 255, 70),
        width=3,
    )
    return draw


def draw_badge(draw: ImageDraw.ImageDraw, text: str, x: int, y: int) -> None:
    font = load_font(18, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 28
    height = bbox[3] - bbox[1] + 18
    draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=(255, 255, 255, 40))
    draw.text((x + 14, y + 9), text, font=font, fill=(248, 251, 255, 255))


def draw_glyph(draw: ImageDraw.ImageDraw, glyph: str, box: tuple[int, int, int, int], theme: dict[str, str]) -> None:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    accent = hex_to_rgb(theme["accent"])
    secondary = tuple(min(channel + 28, 255) for channel in accent)
    outline = (255, 255, 255, 230)
    fill = (*accent, 245)
    soft = (*secondary, 205)
    mid_x = left + width // 2
    mid_y = top + height // 2

    if glyph == "org":
        nodes = [
            (mid_x, top + 40),
            (left + 80, top + 150),
            (mid_x, top + 150),
            (right - 80, top + 150),
        ]
        for node_x, node_y in nodes:
            draw.ellipse((node_x - 24, node_y - 24, node_x + 24, node_y + 24), fill=fill, outline=outline, width=4)
        draw.line((mid_x, top + 64, mid_x, top + 122), fill=outline, width=6)
        draw.line((left + 80, top + 126, right - 80, top + 126), fill=outline, width=6)
        for node_x, _ in nodes[1:]:
            draw.line((node_x, top + 126, node_x, top + 150 - 24), fill=outline, width=6)
    elif glyph == "portal":
        draw.rounded_rectangle((left + 48, top + 42, right - 48, bottom - 42), radius=28, fill=fill, outline=outline, width=4)
        draw.rectangle((left + 48, top + 42, right - 48, top + 94), fill=soft)
        for index in range(3):
            draw.ellipse((left + 76 + index * 28, top + 58, left + 92 + index * 28, top + 74), fill=(255, 255, 255, 220))
        draw.rounded_rectangle((left + 78, top + 126, right - 78, top + 174), radius=18, fill=(255, 255, 255, 215))
        draw.rounded_rectangle((left + 78, top + 198, left + 190, bottom - 76), radius=18, fill=(255, 255, 255, 190))
        draw.rounded_rectangle((left + 214, top + 198, right - 78, bottom - 76), radius=18, fill=(255, 255, 255, 210))
    elif glyph == "tracker":
        for index in range(3):
            row_top = top + 56 + index * 72
            draw.rounded_rectangle((left + 60, row_top, left + 112, row_top + 52), radius=14, fill=fill, outline=outline, width=4)
            draw.line((left + 74, row_top + 28, left + 88, row_top + 40), fill=outline, width=4)
            draw.line((left + 88, row_top + 40, left + 102, row_top + 14), fill=outline, width=4)
            draw.rounded_rectangle((left + 140, row_top + 8, right - 60, row_top + 44), radius=14, fill=(255, 255, 255, 220))
    elif glyph == "message":
        draw.rounded_rectangle((left + 54, top + 72, right - 112, bottom - 110), radius=34, fill=fill, outline=outline, width=4)
        draw.polygon(
            [(left + 170, bottom - 110), (left + 214, bottom - 56), (left + 268, bottom - 110)],
            fill=fill,
            outline=outline,
        )
        draw.rounded_rectangle((left + 180, top + 44, right - 54, bottom - 160), radius=34, fill=soft, outline=outline, width=4)
        for shift in range(3):
            line_top = top + 108 + shift * 46
            draw.rounded_rectangle((left + 94, line_top, right - 148, line_top + 18), radius=9, fill=(255, 255, 255, 220))
    elif glyph == "escalation":
        points = [
            (left + 70, bottom - 70),
            (left + 180, bottom - 182),
            (left + 292, bottom - 120),
            (right - 74, top + 66),
        ]
        draw.line(points, fill=outline, width=10, joint="curve")
        for node_x, node_y in points:
            draw.ellipse((node_x - 24, node_y - 24, node_x + 24, node_y + 24), fill=fill, outline=outline, width=4)
        draw.polygon(
            [(right - 74, top + 66), (right - 122, top + 106), (right - 108, top + 22)],
            fill=fill,
            outline=outline,
        )
    elif glyph == "lock":
        draw.rounded_rectangle((left + 96, top + 128, right - 96, bottom - 64), radius=26, fill=fill, outline=outline, width=4)
        draw.arc((left + 178, top + 32, right - 178, top + 240), start=180, end=360, fill=outline, width=10)
        draw.ellipse((mid_x - 18, top + 218, mid_x + 18, top + 254), fill=outline)
        draw.rectangle((mid_x - 8, top + 248, mid_x + 8, top + 308), fill=outline)
    elif glyph == "reuse":
        centers = [(left + 150, mid_y), (mid_x, top + 104), (right - 150, mid_y)]
        for center_x, center_y in centers:
            draw.rounded_rectangle((center_x - 62, center_y - 48, center_x + 62, center_y + 48), radius=24, fill=fill, outline=outline, width=4)
        draw.arc((left + 120, top + 60, right - 120, bottom - 20), start=205, end=332, fill=outline, width=8)
        draw.polygon([(right - 124, mid_y + 44), (right - 92, mid_y + 16), (right - 86, mid_y + 64)], fill=outline)
    elif glyph == "phishing":
        draw.rounded_rectangle((left + 78, top + 124, right - 104, bottom - 84), radius=24, fill=fill, outline=outline, width=4)
        draw.line((left + 78, top + 124, mid_x, mid_y + 12, right - 104, top + 124), fill=outline, width=6)
        draw.arc((right - 214, top + 42, right - 62, top + 184), start=120, end=350, fill=outline, width=8)
        draw.line((right - 110, top + 132, right - 76, top + 206), fill=outline, width=8)
        draw.arc((right - 112, top + 188, right - 52, top + 234), start=90, end=310, fill=outline, width=8)
    elif glyph == "files":
        draw.rounded_rectangle((left + 96, top + 70, mid_x + 54, bottom - 66), radius=22, fill=fill, outline=outline, width=4)
        draw.polygon([(mid_x + 54, top + 70), (mid_x + 54, top + 148), (mid_x - 24, top + 70)], fill=soft, outline=outline)
        draw.rounded_rectangle((mid_x - 10, top + 124, right - 96, bottom - 92), radius=24, fill=(255, 255, 255, 215), outline=outline, width=4)
        draw.arc((mid_x + 48, top + 92, right - 132, top + 236), start=180, end=360, fill=outline, width=8)
    elif glyph == "incident":
        draw.polygon([(mid_x, top + 48), (right - 86, bottom - 78), (left + 86, bottom - 78)], fill=fill, outline=outline)
        draw.rectangle((mid_x - 10, top + 142, mid_x + 10, top + 252), fill=outline)
        draw.ellipse((mid_x - 12, top + 274, mid_x + 12, top + 298), fill=outline)
    elif glyph == "ownership":
        draw.rounded_rectangle((left + 64, top + 84, right - 64, bottom - 84), radius=28, fill=fill, outline=outline, width=4)
        draw.ellipse((left + 104, top + 124, left + 176, top + 196), fill=(255, 255, 255, 220))
        draw.ellipse((right - 176, top + 124, right - 104, top + 196), fill=(255, 255, 255, 220))
        draw.rounded_rectangle((left + 208, top + 132, right - 208, top + 190), radius=18, fill=(255, 255, 255, 215))
        draw.rounded_rectangle((left + 104, top + 232, right - 104, top + 278), radius=18, fill=(255, 255, 255, 200))
    elif glyph == "empathy":
        draw.rounded_rectangle((left + 76, top + 120, mid_x + 32, bottom - 114), radius=28, fill=fill, outline=outline, width=4)
        draw.polygon([(left + 188, bottom - 114), (left + 230, bottom - 70), (left + 250, bottom - 114)], fill=fill, outline=outline)
        draw.rounded_rectangle((mid_x - 8, top + 78, right - 76, bottom - 156), radius=28, fill=soft, outline=outline, width=4)
        draw.polygon([(right - 188, bottom - 156), (right - 228, bottom - 118), (right - 250, bottom - 156)], fill=soft, outline=outline)
        draw.ellipse((mid_x - 44, top + 204, mid_x + 8, top + 256), fill=(255, 255, 255, 220))
        draw.ellipse((mid_x + 6, top + 204, mid_x + 58, top + 256), fill=(255, 255, 255, 220))
    elif glyph == "complaint":
        draw.rounded_rectangle((left + 120, top + 62, right - 120, bottom - 58), radius=26, fill=fill, outline=outline, width=4)
        draw.rectangle((mid_x - 70, top + 38, mid_x + 70, top + 92), fill=soft, outline=outline, width=4)
        for index in range(3):
            line_top = top + 146 + index * 56
            draw.rounded_rectangle((left + 160, line_top, right - 200, line_top + 18), radius=9, fill=(255, 255, 255, 220))
        draw.ellipse((right - 208, bottom - 154, right - 120, bottom - 66), fill=(255, 255, 255, 230))
        draw.text((right - 181, bottom - 143), "!", font=load_font(44, bold=True), fill=hex_to_rgb(theme["panel"]))
    elif glyph == "deescalation":
        wave_points = [
            (left + 82, top + 168),
            (left + 170, top + 116),
            (left + 260, top + 150),
            (left + 350, top + 94),
            (right - 92, top + 136),
        ]
        draw.line(wave_points, fill=outline, width=10, joint="curve")
        draw.line((left + 120, bottom - 122, right - 120, bottom - 122), fill=(255, 255, 255, 170), width=6)
        draw.arc((mid_x - 94, bottom - 200, mid_x + 94, bottom - 36), start=25, end=155, fill=fill, width=10)
    elif glyph == "deadline":
        draw.ellipse((left + 130, top + 74, right - 130, bottom - 74), fill=fill, outline=outline, width=4)
        draw.line((mid_x, mid_y, mid_x, top + 126), fill=outline, width=8)
        draw.line((mid_x, mid_y, right - 190, mid_y + 46), fill=outline, width=8)
        draw.arc((left + 88, top + 30, right - 88, bottom - 30), start=290, end=35, fill=(255, 255, 255, 170), width=8)
        draw.polygon([(right - 132, top + 100), (right - 92, top + 112), (right - 116, top + 70)], fill=outline)
    else:
        draw.ellipse((left + 120, top + 70, right - 120, bottom - 70), fill=fill, outline=outline, width=4)


def render_cover(filename: str, title: str, subtitle: str, theme_name: str) -> None:
    theme = THEMES[theme_name]
    image = gradient_background(COURSE_COVER_SIZE, theme["start"], theme["end"])
    draw = draw_card_shell(image, theme)
    draw_badge(draw, "Course" if "-en" in filename else "Курс", 92, 88)
    glyph_box = (820, 132, 1080, 390)
    draw_glyph(draw, "portal" if theme_name == "onboarding" else "lock" if theme_name == "security" else "ownership", glyph_box, theme)

    title_font = load_font(44, bold=True)
    subtitle_font = load_font(24, bold=False)
    title_lines = wrap_text(draw, title, title_font, 620)
    subtitle_lines = wrap_text(draw, subtitle, subtitle_font, 620)

    y = 170
    for line in title_lines[:3]:
        draw.text((102, y), line, font=title_font, fill=(248, 251, 255, 255))
        y += 60
    y += 12
    for line in subtitle_lines[:3]:
        draw.text((104, y), line, font=subtitle_font, fill=(235, 242, 250, 232))
        y += 34

    output_path = MEDIA_ROOT / filename
    image.save(output_path)


def render_lesson_image(metadata: dict[str, object], locale: str) -> Path:
    theme = THEMES[str(metadata["theme"])]
    localized = metadata[locale]
    title = str(localized["title"])
    subtitle = str(localized["subtitle"])
    image = gradient_background(LESSON_IMAGE_SIZE, theme["start"], theme["end"])
    draw = draw_card_shell(image, theme)
    draw_badge(draw, "Lesson" if locale == "en" else "Урок", 92, 88)
    glyph_box = (830, 138, 1086, 394)
    draw_glyph(draw, str(metadata["glyph"]), glyph_box, theme)

    kicker_font = load_font(20, bold=True)
    title_font = load_font(38, bold=True)
    subtitle_font = load_font(23, bold=False)
    kicker = (
        "Interactive walkthrough with practice and recap"
        if locale == "en"
        else "Интерактивный разбор с практикой и итогом"
    )
    draw.text((98, 162), kicker, font=kicker_font, fill=(230, 240, 248, 230))

    title_lines = wrap_text(draw, title, title_font, 610)
    subtitle_lines = wrap_text(draw, subtitle, subtitle_font, 610)
    y = 212
    for line in title_lines[:3]:
        draw.text((98, y), line, font=title_font, fill=(248, 251, 255, 255))
        y += 54
    y += 8
    for line in subtitle_lines[:3]:
        draw.text((100, y), line, font=subtitle_font, fill=(236, 243, 248, 232))
        y += 32

    bullet_y = 520
    bullet_font = load_font(18, bold=True)
    chips = (
        ["Фото/схема", "Видео", "Практика"] if locale == "ru" else ["Visual", "Video", "Practice"]
    )
    chip_x = 100
    for chip in chips:
        bbox = draw.textbbox((0, 0), chip, font=bullet_font)
        chip_width = bbox[2] - bbox[0] + 28
        draw.rounded_rectangle(
            (chip_x, bullet_y, chip_x + chip_width, bullet_y + 38),
            radius=19,
            fill=(255, 255, 255, 46),
        )
        draw.text((chip_x + 14, bullet_y + 8), chip, font=bullet_font, fill=(248, 251, 255, 255))
        chip_x += chip_width + 12

    filename = f"{metadata['key']}-{locale}.png"
    output_path = MEDIA_ROOT / filename
    image.save(output_path)
    return output_path


def crop_with_zoom(frame: np.ndarray, progress: float) -> np.ndarray:
    target_w, target_h = VIDEO_SIZE
    source_h, source_w = frame.shape[:2]
    scale = 1.0 + 0.06 * progress
    crop_w = int(source_w / scale)
    crop_h = int(source_h / scale)
    offset_x = int((source_w - crop_w) * (0.22 + 0.18 * math.sin(progress * math.pi)))
    offset_y = int((source_h - crop_h) * (0.18 + 0.16 * math.cos(progress * math.pi * 0.8)))
    offset_x = max(0, min(source_w - crop_w, offset_x))
    offset_y = max(0, min(source_h - crop_h, offset_y))
    cropped = frame[offset_y:offset_y + crop_h, offset_x:offset_x + crop_w]
    return cv2.resize(cropped, VIDEO_SIZE, interpolation=cv2.INTER_LINEAR)


def render_lesson_video(metadata: dict[str, object], locale: str) -> None:
    source_path = MEDIA_ROOT / f"{metadata['key']}-{locale}.png"
    buffer = np.fromfile(str(source_path), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read source image: {source_path}")

    writer = cv2.VideoWriter(
        str(MEDIA_ROOT / f"{metadata['key']}-{locale}.mp4"),
        cv2.VideoWriter_fourcc(*"mp4v"),
        VIDEO_FPS,
        VIDEO_SIZE,
    )
    if not writer.isOpened():
        raise RuntimeError("Failed to open video writer")

    frame_count = int(VIDEO_FPS * VIDEO_DURATION_SECONDS)
    accent = hex_to_rgb(THEMES[str(metadata["theme"])]["accent"])
    accent_bgr = (accent[2], accent[1], accent[0])

    for frame_index in range(frame_count):
        progress = frame_index / max(frame_count - 1, 1)
        frame = crop_with_zoom(image, progress)

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (VIDEO_SIZE[0], 68), (8, 14, 22), -1)
        cv2.rectangle(overlay, (0, VIDEO_SIZE[1] - 82), (VIDEO_SIZE[0], VIDEO_SIZE[1]), (8, 14, 22), -1)
        alpha = 0.52
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        progress_width = int((VIDEO_SIZE[0] - 80) * progress)
        cv2.rectangle(frame, (40, VIDEO_SIZE[1] - 38), (VIDEO_SIZE[0] - 40, VIDEO_SIZE[1] - 24), (220, 226, 232), -1)
        cv2.rectangle(frame, (40, VIDEO_SIZE[1] - 38), (40 + progress_width, VIDEO_SIZE[1] - 24), accent_bgr, -1)

        pulse = 1.0 + 0.08 * math.sin(progress * math.pi * 4)
        radius = int(36 * pulse)
        center = (VIDEO_SIZE[0] // 2, VIDEO_SIZE[1] // 2 + 8)
        cv2.circle(frame, center, radius, (255, 255, 255), -1)
        triangle = np.array(
            [
                (center[0] - 10, center[1] - 14),
                (center[0] - 10, center[1] + 14),
                (center[0] + 18, center[1]),
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(frame, triangle, accent_bgr)

        writer.write(frame)

    writer.release()


def generate_images() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    for item in COURSE_COVERS:
        render_cover(
            filename=str(item["filename"]),
            title=str(item["title"]),
            subtitle=str(item["subtitle"]),
            theme_name=str(item["theme"]),
        )
    for metadata in LESSON_MEDIA:
        for locale in ("ru", "en"):
            render_lesson_image(metadata, locale)


def generate_videos() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    for metadata in LESSON_MEDIA:
        for locale in ("ru", "en"):
            render_lesson_video(metadata, locale)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--images",
        action="store_true",
        help="Generate course covers and lesson images.",
    )
    parser.add_argument(
        "--videos",
        action="store_true",
        help="Generate lesson videos from lesson images.",
    )
    args = parser.parse_args()

    generate_all = not args.images and not args.videos
    if args.images or generate_all:
        generate_images()
    if args.videos or generate_all:
        generate_videos()
    print(f"Thematic media generated in {MEDIA_ROOT}")


if __name__ == "__main__":
    main()

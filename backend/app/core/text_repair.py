from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any


CP1251_EXTRA: dict[str, int] = {
    "\u0402": 0x80,
    "\u0403": 0x81,
    "\u201A": 0x82,
    "\u0453": 0x83,
    "\u201E": 0x84,
    "\u2026": 0x85,
    "\u2020": 0x86,
    "\u2021": 0x87,
    "\u20AC": 0x88,
    "\u2030": 0x89,
    "\u0409": 0x8A,
    "\u2039": 0x8B,
    "\u040A": 0x8C,
    "\u040C": 0x8D,
    "\u040B": 0x8E,
    "\u040F": 0x8F,
    "\u0452": 0x90,
    "\u2018": 0x91,
    "\u2019": 0x92,
    "\u201C": 0x93,
    "\u201D": 0x94,
    "\u2022": 0x95,
    "\u2013": 0x96,
    "\u2014": 0x97,
    "\u2122": 0x99,
    "\u0459": 0x9A,
    "\u203A": 0x9B,
    "\u045A": 0x9C,
    "\u045C": 0x9D,
    "\u045B": 0x9E,
    "\u045F": 0x9F,
    "\u00A0": 0xA0,
    "\u040E": 0xA1,
    "\u045E": 0xA2,
    "\u0408": 0xA3,
    "\u00A4": 0xA4,
    "\u0490": 0xA5,
    "\u00A6": 0xA6,
    "\u00A7": 0xA7,
    "\u0401": 0xA8,
    "\u00A9": 0xA9,
    "\u0404": 0xAA,
    "\u00AB": 0xAB,
    "\u00AC": 0xAC,
    "\u00AD": 0xAD,
    "\u00AE": 0xAE,
    "\u0407": 0xAF,
    "\u00B0": 0xB0,
    "\u00B1": 0xB1,
    "\u0406": 0xB2,
    "\u0456": 0xB3,
    "\u0491": 0xB4,
    "\u00B5": 0xB5,
    "\u00B6": 0xB6,
    "\u00B7": 0xB7,
    "\u0451": 0xB8,
    "\u2116": 0xB9,
    "\u0454": 0xBA,
    "\u00BB": 0xBB,
    "\u0458": 0xBC,
    "\u0405": 0xBD,
    "\u0455": 0xBE,
    "\u0457": 0xBF,
}

WINDOWS_1252_ALIAS: dict[str, int] = {
    "\u20AC": 0x80,
    "\u0081": 0x81,
    "\u201A": 0x82,
    "\u0192": 0x83,
    "\u201E": 0x84,
    "\u2026": 0x85,
    "\u2020": 0x86,
    "\u2021": 0x87,
    "\u02C6": 0x88,
    "\u2030": 0x89,
    "\u0160": 0x8A,
    "\u2039": 0x8B,
    "\u0152": 0x8C,
    "\u008D": 0x8D,
    "\u017D": 0x8E,
    "\u008F": 0x8F,
    "\u0090": 0x90,
    "\u2018": 0x91,
    "\u2019": 0x92,
    "\u201C": 0x93,
    "\u201D": 0x94,
    "\u2022": 0x95,
    "\u2013": 0x96,
    "\u2014": 0x97,
    "\u02DC": 0x98,
    "\u2122": 0x99,
    "\u0161": 0x9A,
    "\u203A": 0x9B,
    "\u0153": 0x9C,
    "\u009D": 0x9D,
    "\u017E": 0x9E,
    "\u0178": 0x9F,
}


def _encode_mojibake_bytes(value: str) -> bytes | None:
    encoded = bytearray()
    for char in value:
        code = ord(char)
        if code <= 0x7F:
            encoded.append(code)
            continue
        if 0x80 <= code <= 0x9F:
            encoded.append(code)
            continue
        if char == "\u0401":
            encoded.append(0xA8)
            continue
        if char == "\u0451":
            encoded.append(0xB8)
            continue
        if 0x0410 <= code <= 0x042F:
            encoded.append(code - 0x0410 + 0xC0)
            continue
        if 0x0430 <= code <= 0x044F:
            encoded.append(code - 0x0430 + 0xE0)
            continue
        if char in CP1251_EXTRA:
            encoded.append(CP1251_EXTRA[char])
            continue
        if char in WINDOWS_1252_ALIAS:
            encoded.append(WINDOWS_1252_ALIAS[char])
            continue
        return None
    return bytes(encoded)


def repair_mojibake_text(value: str) -> str:
    if not value:
        return value

    repaired = value
    for _ in range(2):
        try:
            raw_bytes = _encode_mojibake_bytes(repaired)
            if raw_bytes is None:
                break
            candidate = raw_bytes.decode("utf-8")
        except UnicodeError:
            break
        if candidate == repaired:
            break
        repaired = candidate
    return repaired


def repair_text_payload(value: Any) -> Any:
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if is_dataclass(value):
        for field in fields(value):
            setattr(value, field.name, repair_text_payload(getattr(value, field.name)))
        return value
    if isinstance(value, list):
        return [repair_text_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_text_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: repair_text_payload(item) for key, item in value.items()}
    return value

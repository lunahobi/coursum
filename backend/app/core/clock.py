"""Time utilities. Always work in UTC."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


def naive_utcnow() -> datetime:
    """Return current UTC time as naive datetime for legacy DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)

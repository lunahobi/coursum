import pytest

from app.core.config import Settings


def test_production_requires_strong_secret():
    with pytest.raises(ValueError):
        Settings(environment="production", secret_key="change-me-in-production", cors_origins=["https://coursum.online"])


def test_production_disallows_localhost_cors():
    with pytest.raises(ValueError):
        Settings(
            environment="production",
            secret_key="x" * 32,
            cors_origins=["http://localhost:5173", "https://coursum.online"],
        )

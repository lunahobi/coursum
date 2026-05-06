from functools import lru_cache
from typing import Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Corporate LMS"
    environment: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./lms.db"
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 30
    refresh_token_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://coursum.online",
            "https://www.coursum.online",
        ]
    )
    allow_tenant_header_fallback: bool = True
    tenant_header_name: str = "X-Tenant-Code"
    demo_notification_target: str = "mock://notifications"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LMS_", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> List[str]:
        # Accept JSON array or comma-separated origins from env.
        if value is None:
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    import json

                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

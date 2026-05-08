from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes.analytics import router as analytics_router
from app.api.routes.assignments import router as assignments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.courses import router as courses_router
from app.api.routes.groups import router as groups_router
from app.api.routes.lessons import router as lessons_router
from app.api.routes.media import router as media_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes.tests import router as tests_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.db import SessionLocal

settings = get_settings()
static_root = Path(__file__).resolve().parent / "static"
media_root = static_root / "media"
media_root.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https://([a-z0-9-]+\.)?coursum\.online$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", settings.tenant_header_name],
)
app.mount("/media", StaticFiles(directory=media_root), name="media")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}


for router in [auth_router, tenants_router, users_router, groups_router, courses_router, lessons_router, media_router, tests_router, recommendations_router, assignments_router, analytics_router]:
    app.include_router(router, prefix=settings.api_prefix)

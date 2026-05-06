from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.analytics import router as analytics_router
from app.api.routes.assignments import router as assignments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.courses import router as courses_router
from app.api.routes.media import router as media_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes.tests import router as tests_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.db import Base, engine
from app.core.schema import ensure_runtime_schema


settings = get_settings()
static_root = Path(__file__).resolve().parent / "static"
media_root = static_root / "media"
media_root.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=media_root), name="media")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


for router in [auth_router, tenants_router, users_router, courses_router, media_router, tests_router, recommendations_router, assignments_router, analytics_router]:
    app.include_router(router, prefix=settings.api_prefix)

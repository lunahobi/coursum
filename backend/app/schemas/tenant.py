from pydantic import BaseModel

from app.schemas.common import ORMModel


class TenantRead(ORMModel):
    id: int
    name: str
    code: str
    locale: str


class TenantSelectRequest(BaseModel):
    code: str


class TenantCreate(BaseModel):
    name: str
    code: str
    locale: str = "ru"


class TenantUpdate(BaseModel):
    name: str | None = None
    locale: str | None = None
    is_active: bool | None = None

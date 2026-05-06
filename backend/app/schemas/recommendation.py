from pydantic import BaseModel

from app.schemas.common import ORMModel


class EditorRecommendationCreate(BaseModel):
    title: str
    text: str = ""
    course_id: int | None = None
    lesson_id: int | None = None
    sort_order: int = 0
    is_active: bool = True


class EditorRecommendationUpdate(EditorRecommendationCreate):
    pass


class EditorRecommendationRead(ORMModel):
    id: int
    tenant_id: int
    title: str
    text: str
    course_id: int | None = None
    lesson_id: int | None = None
    sort_order: int
    is_active: bool

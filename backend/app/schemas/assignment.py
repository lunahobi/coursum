from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


ASSIGNMENT_STATUSES = {
    "not_started",
    "draft",
    "submitted",
    "in_review",
    "approved",
    "needs_revision",
    "rejected",
}


class AssignmentCreate(BaseModel):
    course_id: int
    lesson_id: int | None = None
    title: str
    description: str = ""
    is_active: bool = True
    due_at: datetime | None = None


class AssignmentUpdate(BaseModel):
    title: str
    description: str = ""
    is_active: bool = True
    due_at: datetime | None = None


class AssignmentRead(ORMModel):
    id: int
    course_id: int
    lesson_id: int | None = None
    title: str
    description: str
    is_active: bool
    due_at: datetime | None = None
    created_at: datetime


class SubmissionUpsert(BaseModel):
    status: str = "draft"
    text_answer: str = ""
    link_answer: str | None = None
    file_urls: list[str] = Field(default_factory=list)


class SubmissionReviewCreate(BaseModel):
    status: str
    comment: str = ""


class SubmissionFileRead(ORMModel):
    id: int
    file_url: str
    file_name: str
    created_at: datetime


class SubmissionReviewRead(ORMModel):
    id: int
    reviewer_user_id: int
    status: str
    comment: str
    created_at: datetime


class AssignmentSubmissionRead(ORMModel):
    id: int
    assignment_id: int
    student_user_id: int
    status: str
    text_answer: str
    link_answer: str | None = None
    submitted_at: datetime | None = None
    updated_at: datetime
    files: list[SubmissionFileRead] = Field(default_factory=list)
    latest_review: SubmissionReviewRead | None = None

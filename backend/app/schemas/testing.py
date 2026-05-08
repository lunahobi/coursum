from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TestCreate(BaseModel):
    course_id: int
    title: str
    baseline_difficulty: int = 3
    question_limit: int = 10


class TestUpdate(BaseModel):
    title: str
    baseline_difficulty: int = Field(default=3, ge=1, le=5)
    question_limit: int = Field(default=10, ge=1, le=50)


class QuestionCreate(BaseModel):
    test_id: int
    text: str
    explanation: str = ""
    difficulty: int
    estimated_seconds: int = 30
    shuffle_options: bool = False
    topic_ids: list[int]
    options: list[dict]


class SubmitAnswerRequest(BaseModel):
    question_id: int
    answer_option_id: int | None = None
    response_seconds: int = 0


class QuestionOptionRead(BaseModel):
    id: int
    text: str


class QuestionRead(ORMModel):
    id: int
    text: str
    difficulty: int
    estimated_seconds: int
    question_number: int = 1
    total_questions: int = 1
    remaining_questions: int = 0
    target_difficulty: int = 3
    topic_titles: list[str] = Field(default_factory=list)
    options: list[QuestionOptionRead]

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LessonBlock(BaseModel):
    type: str
    text: str | None = None
    html: str | None = None
    url: str | None = None
    alt: str | None = None
    title: str | None = None
    status: str | None = None
    error: str | None = None


class LessonPage(BaseModel):
    page_id: str | None = None
    chapter_title: str
    page_title: str
    blocks: list[LessonBlock] = Field(default_factory=list)


class CourseCreate(BaseModel):
    title: str
    description: str = ""
    image_url: str | None = None
    status: str = "draft"
    category: str | None = None
    access_settings: dict | None = None
    available_from: datetime | None = None
    available_to: datetime | None = None


class CourseUpdate(CourseCreate):
    pass


class CourseRead(ORMModel):
    id: int
    title: str
    description: str
    is_published: bool
    status: str = "draft"
    image_url: str | None = None
    category: str | None = None
    access_settings: dict = Field(default_factory=dict)
    available_from: datetime | None = None
    available_to: datetime | None = None


class CourseStatusUpdate(BaseModel):
    status: str


class SectionCreate(BaseModel):
    title: str
    sort_order: int = 0
    is_visible: bool = True


class SectionUpdate(SectionCreate):
    pass


class SectionReorderRequest(BaseModel):
    section_ids: list[int] = Field(default_factory=list)


class LessonReorderRequest(BaseModel):
    lesson_ids: list[int] = Field(default_factory=list)


class LessonFlagUpdate(BaseModel):
    value: bool


class LessonCreate(BaseModel):
    course_id: int
    section_id: int | None = None
    topic_id: int | None = None
    title: str
    summary: str = ""
    content: str
    content_pages: list[LessonPage] | None = None
    duration_minutes: int = 8
    image_url: str | None = None
    video_url: str | None = None
    is_visible: bool = True
    is_published: bool = True
    sort_order: int = 0


class LessonUpdate(LessonCreate):
    pass


class LessonRead(ORMModel):
    id: int
    course_id: int
    section_id: int | None = None
    title: str
    summary: str
    content: str
    content_pages: list[LessonPage] | None = None
    duration_minutes: int
    image_url: str | None = None
    video_url: str | None = None
    is_visible: bool = True
    is_published: bool = True
    sort_order: int


class SectionRead(ORMModel):
    id: int
    course_id: int
    title: str
    sort_order: int
    is_visible: bool


class AssignmentRequest(BaseModel):
    user_id: int | None = None
    group_id: int | None = None


class StaffAssignmentRequest(BaseModel):
    user_id: int
    role_name: str = "teacher"


class SectionOutlineItem(BaseModel):
    id: int
    title: str
    sort_order: int
    is_visible: bool


class LessonOutlineItem(BaseModel):
    id: int
    section_id: int | None = None
    title: str
    summary: str
    sort_order: int
    duration_minutes: int
    page_count: int
    current_page_index: int
    is_completed: bool
    is_current: bool
    has_video: bool


class CourseOutlineRead(BaseModel):
    course_id: int
    course_title: str
    description: str
    total_lessons: int
    completed_lessons: int
    progress_percent: int
    resume_lesson_id: int | None = None
    sections: list[SectionOutlineItem] = Field(default_factory=list)
    lessons: list[LessonOutlineItem]


class LessonChapterRead(BaseModel):
    chapter_title: str
    pages: list[dict]


class LessonPlayerState(BaseModel):
    current_page_index: int
    completed_page_ids: list[str] = Field(default_factory=list)
    is_completed: bool = False
    last_video_position_seconds: int = 0


class LessonPlayerRead(BaseModel):
    course_id: int
    course_title: str
    lesson_id: int
    lesson_title: str
    summary: str
    duration_minutes: int
    pages: list[LessonPage]
    chapters: list[LessonChapterRead]
    outline: CourseOutlineRead
    state: LessonPlayerState
    previous_lesson_id: int | None = None
    next_lesson_id: int | None = None


class LessonStateUpdate(BaseModel):
    current_page_index: int | None = None
    completed_page_ids: list[str] | None = None
    last_video_position_seconds: int | None = None
    is_completed: bool | None = None

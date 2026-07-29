from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """작업 상태. Notion 상태 속성과 매핑."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(StrEnum):
    """우선순위. AI 스케줄링 및 정렬에 사용."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseModel):
    """Task 스키마 공통 필드."""

    title: str = Field(..., min_length=1, max_length=300, examples=["PR #42 리뷰"])
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    tags: list[str] = Field(default_factory=list, examples=[["work", "backend"]])
    due_date: datetime | None = None
    estimated_duration: int | None = Field(
        default=None,
        ge=1,
        le=14400,
        description="예상 소요 시간 (분 단위, 최대 10일)",
    )


class TaskCreate(TaskBase):
    """작업 생성 요청 스키마."""

    pass


class TaskUpdate(BaseModel):
    """작업 부분 수정 요청 스키마 (PATCH). 모든 필드 선택적."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    tags: list[str] | None = None
    due_date: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=14400)


class SubTaskCreate(BaseModel):
    """서브태스크 생성 요청."""

    title: str = Field(..., min_length=1, max_length=300)
    position: int = Field(default=0, ge=0)


class SubTaskUpdate(BaseModel):
    """서브태스크 수정 요청."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    is_completed: bool | None = None
    position: int | None = Field(default=None, ge=0)


class SubTaskResponse(BaseModel):
    """서브태스크 응답."""

    id: UUID
    task_id: UUID
    title: str
    is_completed: bool
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NaturalLanguageInput(BaseModel):
    """자연어 입력으로 태스크 생성 요청."""

    text: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        examples=["내일까지 분기 보고서 작성해야 함, 급함"],
    )


class AISuggestionResponse(BaseModel):
    """AI 추천 분석 결과."""

    suggestion: str


class TaskResponse(TaskBase):
    """API 응답용 전체 Task 스키마."""

    id: UUID = Field(default_factory=uuid4)
    ai_suggestion: str | None = Field(
        default=None,
        description="AI가 생성한 작업 추천 내용",
    )
    notion_page_id: str | None = Field(
        default=None,
        description="Notion 동기화용 페이지 ID",
    )
    subtasks: list[SubTaskResponse] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"from_attributes": True}


class TaskStatsResponse(BaseModel):
    """태스크 통계 대시보드 응답."""

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    overdue: int
    completed_today: int
    completion_rate: float

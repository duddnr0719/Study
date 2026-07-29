from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import Task
from app.schemas.task import (
    AISuggestionResponse,
    NaturalLanguageInput,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatsResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services.ai_service import parse_natural_language, suggest_task_improvements
from app.services.notion_service import (
    fetch_tasks_from_notion,
    sync_task_to_notion,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/stats", response_model=TaskStatsResponse)
def get_task_stats(db: Session = Depends(get_db)) -> dict:
    """태스크 통계 대시보드."""
    total = db.scalar(select(func.count(Task.id))) or 0

    # 상태별 카운트
    status_rows = db.execute(
        select(Task.status, func.count(Task.id)).group_by(Task.status)
    ).all()
    by_status = {row[0]: row[1] for row in status_rows}

    # 우선순위별 카운트
    priority_rows = db.execute(
        select(Task.priority, func.count(Task.id)).group_by(Task.priority)
    ).all()
    by_priority = {row[0]: row[1] for row in priority_rows}

    # 마감 지난 태스크 수
    now = datetime.now(UTC)
    overdue = db.scalar(
        select(func.count(Task.id)).where(
            Task.due_date < now, Task.status != "done"
        )
    ) or 0

    # 오늘 완료된 태스크 수
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = db.scalar(
        select(func.count(Task.id)).where(
            Task.status == "done", Task.updated_at >= today_start
        )
    ) or 0

    done_count = by_status.get("done", 0)
    completion_rate = (done_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
        "completed_today": completed_today,
        "completion_rate": round(completion_rate, 1),
    }


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)) -> Task:
    """새 태스크 생성."""
    task = Task(**body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    search: str | None = Query(default=None, description="제목/설명 검색어"),
    tag: str | None = Query(default=None, description="태그 필터"),
    sort_by: str = Query(default="created_at", description="정렬 기준: created_at, due_date, priority, title"),
    sort_order: str = Query(default="desc", description="정렬 방향: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Task]:
    """태스크 목록 조회. 검색, 필터, 정렬, 페이지네이션 지원."""
    stmt = select(Task)

    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Task.title.ilike(pattern) | Task.description.ilike(pattern))
    # 정렬
    sort_column = getattr(Task, sort_by, Task.created_at)
    if sort_order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    tasks = list(db.scalars(stmt).all())

    # 태그 필터 (JSON 배열이라 Python 레벨에서 필터링)
    if tag:
        tasks = [t for t in tasks if tag in (t.tags or [])]

    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, db: Session = Depends(get_db)) -> Task:
    """단일 태스크 조회."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID, body: TaskUpdate, db: Session = Depends(get_db)
) -> Task:
    """태스크 부분 수정 (PATCH)."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: UUID, db: Session = Depends(get_db)) -> None:
    """태스크 삭제."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()


@router.post("/parse", response_model=TaskResponse, status_code=201)
def create_task_from_natural_language(
    body: NaturalLanguageInput, db: Session = Depends(get_db)
) -> Task:
    """자연어 입력을 AI로 파싱하여 태스크 자동 생성.

    예: "내일까지 분기 보고서 작성, 급함" → 구조화된 태스크
    """
    try:
        parsed = parse_natural_language(body.text)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI 파싱 실패: {e}",
        )

    task = Task(
        title=parsed.get("title", body.text[:100]),
        description=parsed.get("description"),
        priority=parsed.get("priority", "medium"),
        tags=parsed.get("tags", []),
        due_date=parsed.get("due_date"),
        estimated_duration=parsed.get("estimated_duration"),
        ai_suggestion=f"원본 입력: {body.text}",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/ai/suggestions", response_model=AISuggestionResponse)
def get_ai_suggestions(db: Session = Depends(get_db)) -> dict:
    """현재 미완료 태스크 목록을 AI가 분석하고 우선순위/일정 추천을 반환."""
    stmt = (
        select(Task)
        .where(Task.status != "done")
        .order_by(Task.created_at.desc())
        .limit(50)
    )
    tasks = list(db.scalars(stmt).all())

    if not tasks:
        return {"suggestion": "현재 등록된 미완료 태스크가 없습니다."}

    tasks_data = [
        {
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "tags": t.tags,
            "due_date": str(t.due_date) if t.due_date else None,
            "estimated_duration": t.estimated_duration,
            "created_at": str(t.created_at),
        }
        for t in tasks
    ]

    try:
        suggestion = suggest_task_improvements(tasks_data)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI 추천 생성 실패: {e}",
        )

    return {"suggestion": suggestion}


@router.post("/{task_id}/sync", response_model=TaskResponse)
def sync_task_to_notion_endpoint(
    task_id: UUID, db: Session = Depends(get_db)
) -> Task:
    """단일 태스크를 Notion에 동기화 (생성 또는 업데이트)."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    notion_page_id = sync_task_to_notion(task)
    if notion_page_id is None:
        raise HTTPException(status_code=502, detail="Notion 동기화 실패")

    task.notion_page_id = notion_page_id
    db.commit()
    db.refresh(task)
    return task


@router.post("/sync/all", response_model=list[TaskResponse])
def sync_all_tasks_to_notion(db: Session = Depends(get_db)) -> list[Task]:
    """모든 미완료 태스크를 Notion에 일괄 동기화."""
    stmt = select(Task).where(Task.status != "done")
    tasks = list(db.scalars(stmt).all())

    synced = []
    for task in tasks:
        notion_page_id = sync_task_to_notion(task)
        if notion_page_id:
            task.notion_page_id = notion_page_id
            synced.append(task)

    db.commit()
    for task in synced:
        db.refresh(task)
    return synced


@router.post("/sync/from-notion", response_model=list[TaskResponse], status_code=201)
def import_tasks_from_notion(db: Session = Depends(get_db)) -> list[Task]:
    """Notion DB에서 태스크를 가져와 백엔드 DB에 저장 (Notion → 백엔드)."""
    notion_tasks = fetch_tasks_from_notion()
    imported = []

    for nt in notion_tasks:
        # 이미 동기화된 태스크인지 확인
        existing = db.scalars(
            select(Task).where(Task.notion_page_id == nt["notion_page_id"])
        ).first()

        if existing:
            # 기존 태스크 업데이트
            existing.title = nt["title"]
            existing.status = nt["status"]
            existing.priority = nt["priority"]
            existing.tags = nt["tags"]
            existing.due_date = nt.get("due_date")
            existing.ai_suggestion = nt.get("ai_suggestion")
            imported.append(existing)
        else:
            # 새 태스크 생성
            task = Task(
                title=nt["title"],
                status=nt["status"],
                priority=nt["priority"],
                tags=nt["tags"],
                due_date=nt.get("due_date"),
                ai_suggestion=nt.get("ai_suggestion"),
                notion_page_id=nt["notion_page_id"],
            )
            db.add(task)
            imported.append(task)

    db.commit()
    for task in imported:
        db.refresh(task)
    return imported

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.subtask import SubTask
from app.models.task import Task
from app.schemas.task import SubTaskCreate, SubTaskResponse, SubTaskUpdate

router = APIRouter(prefix="/tasks/{task_id}/subtasks", tags=["subtasks"])


def _get_task_or_404(task_id: UUID, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=SubTaskResponse, status_code=201)
def create_subtask(
    task_id: UUID, body: SubTaskCreate, db: Session = Depends(get_db)
) -> SubTask:
    """서브태스크 생성."""
    _get_task_or_404(task_id, db)
    subtask = SubTask(task_id=task_id, **body.model_dump())
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask


@router.get("", response_model=list[SubTaskResponse])
def list_subtasks(
    task_id: UUID, db: Session = Depends(get_db)
) -> list[SubTask]:
    """태스크의 서브태스크 목록 조회."""
    _get_task_or_404(task_id, db)
    stmt = (
        select(SubTask)
        .where(SubTask.task_id == task_id)
        .order_by(SubTask.position)
    )
    return list(db.scalars(stmt).all())


@router.patch("/{subtask_id}", response_model=SubTaskResponse)
def update_subtask(
    task_id: UUID,
    subtask_id: UUID,
    body: SubTaskUpdate,
    db: Session = Depends(get_db),
) -> SubTask:
    """서브태스크 수정."""
    _get_task_or_404(task_id, db)
    subtask = db.get(SubTask, subtask_id)
    if subtask is None or subtask.task_id != task_id:
        raise HTTPException(status_code=404, detail="SubTask not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(subtask, field, value)

    db.commit()
    db.refresh(subtask)
    return subtask


@router.delete("/{subtask_id}", status_code=204)
def delete_subtask(
    task_id: UUID, subtask_id: UUID, db: Session = Depends(get_db)
) -> None:
    """서브태스크 삭제."""
    _get_task_or_404(task_id, db)
    subtask = db.get(SubTask, subtask_id)
    if subtask is None or subtask.task_id != task_id:
        raise HTTPException(status_code=404, detail="SubTask not found")

    db.delete(subtask)
    db.commit()

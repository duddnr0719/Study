import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SubTask(Base):
    """서브태스크 테이블. 상위 Task에 종속."""

    __tablename__ = "subtasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    task: Mapped["Task"] = relationship(back_populates="subtasks")  # noqa: F821

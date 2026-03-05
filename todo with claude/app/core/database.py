from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=settings.debug)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """모든 모델의 베이스 클래스."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성: 요청마다 DB 세션을 생성하고 종료."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

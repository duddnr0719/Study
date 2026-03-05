import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.subtasks import router as subtasks_router
from app.api.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.database import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기: 시작 및 종료 로직."""
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "내부 서버 오류가 발생했습니다."},
        )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "healthy", "version": settings.app_version}

    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(subtasks_router, prefix="/api/v1")

    return app


app = create_app()

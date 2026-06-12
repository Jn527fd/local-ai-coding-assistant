from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.repos import router as repos_router

logger = logging.getLogger(__name__)


class RootResponse(BaseModel):
    """Basic application metadata returned by the root endpoint."""

    name: str
    version: str
    environment: str
    docs_url: str


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Starting %s version %s",
            app_settings.app_name,
            app_settings.app_version,
        )
        application.state.settings = app_settings
        yield
        logger.info("Stopping %s", app_settings.app_name)

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.app_debug,
        description="A self-hosted API for a local AI coding assistant.",
        lifespan=lifespan,
    )
    application.state.settings = app_settings

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(repos_router)

    @application.get("/", response_model=RootResponse, tags=["application"])
    async def root() -> RootResponse:
        return RootResponse(
            name=app_settings.app_name,
            version=app_settings.app_version,
            environment=app_settings.app_environment,
            docs_url="/docs",
        )

    return application


app = create_app()

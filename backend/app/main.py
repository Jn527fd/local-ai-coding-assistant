from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.auth.credentials import CredentialsService
from app.auth.session import SessionService
from app.routers.account import router as account_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.models import router as models_router
from app.routers.repos import router as repos_router
from app.services.local_settings_service import LocalSettingsService
from app.services.model_manager import ModelManager
from app.services.ollama_service import OllamaService
from app.utils.logging import configure_logging

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
    configure_logging(debug=app_settings.app_debug)
    credentials_service = CredentialsService(
        app_settings.resolved_credentials_file
    )
    session_service = SessionService(ttl_hours=app_settings.session_ttl_hours)
    local_settings_service = LocalSettingsService(
        app_settings.resolved_local_settings_file
    )
    model_manager = ModelManager(
        ollama_service=OllamaService(
            base_url=app_settings.ollama_base_url,
            timeout_seconds=app_settings.ollama_timeout_seconds,
        ),
        local_settings=local_settings_service,
        default_model=app_settings.default_model,
        pull_timeout_seconds=app_settings.model_pull_timeout_seconds,
        delete_previous_model=app_settings.delete_previous_model,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Starting %s version %s",
            app_settings.app_name,
            app_settings.app_version,
        )
        application.state.settings = app_settings
        application.state.credentials_service = credentials_service
        application.state.session_service = session_service
        application.state.local_settings_service = local_settings_service
        application.state.model_manager = model_manager
        try:
            yield
        finally:
            await model_manager.close()
            logger.info("Stopping %s", app_settings.app_name)

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.app_debug,
        description="A self-hosted API for a local AI coding assistant.",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.credentials_service = credentials_service
    application.state.session_service = session_service
    application.state.local_settings_service = local_settings_service
    application.state.model_manager = model_manager

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(account_router)
    application.include_router(models_router)
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

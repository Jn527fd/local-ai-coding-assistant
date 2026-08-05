from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ai.compressors import ContextCompressionManager
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.execution_context import AISettingsResolver
from app.ai.pipelines import DocumentRetrievalPipeline
from app.ai.providers import OllamaLLMProvider
from app.ai.rerankers import OllamaRerankerProvider
from app.ai.vectorstores import VectorStoreManager
from app.config import Settings, get_settings
from app.auth.credentials import CredentialsService
from app.auth.rate_limit import LoginRateLimiter
from app.auth.session import SessionService
from app.middleware.security_headers import add_security_headers
from app.metadata import MetadataMigrationManager, MetadataStore
from app.routers.account import router as account_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.components import router as components_router
from app.routers.conversations import router as conversations_router
from app.routers.documents import router as documents_router
from app.routers.diagnostics import router as diagnostics_router
from app.routers.health import router as health_router
from app.routers.jobs import router as jobs_router
from app.routers.memories import router as memories_router
from app.routers.models import router as models_router
from app.routers.repos import router as repos_router
from app.routers.vectorstores import router as vectorstores_router
from app.services.component_registry import ComponentRegistry
from app.services.conversation_service import ConversationPersistenceService
from app.services.document_service import DocumentService
from app.services.diagnostics import DiagnosticsService
from app.services.job_service import JobService
from app.services.conversation_memory import ConversationMemoryService
from app.services.local_settings_service import LocalSettingsService
from app.services.model_manager import ModelManager
from app.services.ollama_service import OllamaService
from app.services.vision_artifacts import VisionArtifactService
from app.services.audit_log import AuditLogger
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
    session_service = SessionService(
        ttl_hours=app_settings.session_ttl_hours,
        signing_key=app_settings.session_signing_key.get_secret_value(),
    )
    login_rate_limiter = LoginRateLimiter(
        attempts=app_settings.login_rate_limit_attempts,
        window_seconds=app_settings.login_rate_limit_window_seconds,
        lockout_seconds=app_settings.login_lockout_seconds,
    )
    audit_logger = AuditLogger()
    local_settings_service = LocalSettingsService(
        app_settings.resolved_local_settings_file
    )
    metadata_store = MetadataStore(app_settings.resolved_metadata_database_file)
    metadata_migration_manager = MetadataMigrationManager(
        store=metadata_store,
        settings=app_settings,
    )
    model_manager = ModelManager(
        ollama_service=OllamaService(
            base_url=app_settings.ollama_base_url,
            timeout_seconds=app_settings.ollama_timeout_seconds,
            num_predict=app_settings.ollama_num_predict,
            think=app_settings.ollama_think,
            keep_alive=app_settings.ollama_keep_alive,
        ),
        local_settings=local_settings_service,
        default_model=app_settings.default_model,
    )
    vector_store_manager = VectorStoreManager(
        index_directory=app_settings.vector_index_directory,
        backend=app_settings.vector_store_backend,
        qdrant_url=app_settings.qdrant_url,
        qdrant_api_key=app_settings.qdrant_api_key.get_secret_value(),
    )
    component_registry = ComponentRegistry(
        ollama_service=model_manager.ollama_service,
        vector_store_manager=vector_store_manager,
    )
    job_service = JobService(metadata_store=metadata_store)
    document_service = DocumentService(
        upload_directory=app_settings.upload_directory,
        max_upload_bytes=app_settings.document_max_upload_bytes,
        chunk_size=app_settings.document_chunk_size,
        max_chunks=app_settings.document_max_chunks,
    )
    conversation_service = ConversationPersistenceService(
        storage_directory=app_settings.conversation_directory,
        max_conversations_per_user=app_settings.conversation_max_count,
        metadata_store=metadata_store,
    )
    vector_store = vector_store_manager.default_store()
    ai_settings_resolver = AISettingsResolver(
        component_registry=component_registry,
    )
    llm_provider = OllamaLLMProvider(
        ollama_service=model_manager.ollama_service,
    )
    embedder_provider = OllamaEmbedderProvider(
        ollama_service=model_manager.ollama_service,
    )
    reranker_provider = OllamaRerankerProvider(
        ollama_service=model_manager.ollama_service,
    )
    retrieval_pipeline = DocumentRetrievalPipeline(
        embedder_provider=embedder_provider,
        vector_store=vector_store,
    )
    conversation_memory_service = ConversationMemoryService(
        vector_store=vector_store_manager.qdrant_store,
        embedder_provider=embedder_provider,
        collection_name=app_settings.memory_collection_name,
        min_importance=app_settings.memory_min_importance,
    )
    vision_artifact_service = VisionArtifactService(
        storage_directory=app_settings.vision_artifact_directory,
        ollama_service=model_manager.ollama_service,
    )
    context_compression_manager = ContextCompressionManager(
        llm_provider=llm_provider,
    )
    diagnostics_service = DiagnosticsService(
        settings=app_settings,
        document_service=document_service,
        job_service=job_service,
        model_manager=model_manager,
        vector_store_manager=vector_store_manager,
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
        application.state.login_rate_limiter = login_rate_limiter
        application.state.audit_logger = audit_logger
        application.state.local_settings_service = local_settings_service
        application.state.metadata_store = metadata_store
        application.state.metadata_migration_manager = metadata_migration_manager
        application.state.metadata_migration_result = (
            metadata_migration_manager.migrate()
        )
        application.state.model_manager = model_manager
        application.state.component_registry = component_registry
        application.state.job_service = job_service
        application.state.document_service = document_service
        application.state.conversation_service = conversation_service
        application.state.vector_store_manager = vector_store_manager
        application.state.vector_store = vector_store
        application.state.ai_settings_resolver = ai_settings_resolver
        application.state.llm_provider = llm_provider
        application.state.embedder_provider = embedder_provider
        application.state.reranker_provider = reranker_provider
        application.state.retrieval_pipeline = retrieval_pipeline
        application.state.conversation_memory_service = conversation_memory_service
        application.state.vision_artifact_service = vision_artifact_service
        application.state.context_compression_manager = context_compression_manager
        application.state.diagnostics_service = diagnostics_service
        try:
            yield
        finally:
            vector_store_manager.close()
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
    application.state.login_rate_limiter = login_rate_limiter
    application.state.audit_logger = audit_logger
    application.state.local_settings_service = local_settings_service
    application.state.metadata_store = metadata_store
    application.state.metadata_migration_manager = metadata_migration_manager
    application.state.metadata_migration_result = None
    application.state.model_manager = model_manager
    application.state.component_registry = component_registry
    application.state.job_service = job_service
    application.state.document_service = document_service
    application.state.conversation_service = conversation_service
    application.state.vector_store_manager = vector_store_manager
    application.state.vector_store = vector_store
    application.state.ai_settings_resolver = ai_settings_resolver
    application.state.llm_provider = llm_provider
    application.state.embedder_provider = embedder_provider
    application.state.reranker_provider = reranker_provider
    application.state.retrieval_pipeline = retrieval_pipeline
    application.state.conversation_memory_service = conversation_memory_service
    application.state.vision_artifact_service = vision_artifact_service
    application.state.context_compression_manager = context_compression_manager
    application.state.diagnostics_service = diagnostics_service

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_origin_regex=app_settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(add_security_headers)

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(account_router)
    application.include_router(models_router)
    application.include_router(components_router)
    application.include_router(conversations_router)
    application.include_router(jobs_router)
    application.include_router(documents_router)
    application.include_router(diagnostics_router)
    application.include_router(vectorstores_router)
    application.include_router(memories_router)
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

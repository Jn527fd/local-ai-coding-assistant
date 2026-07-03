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
from app.auth.session import SessionService
from app.metadata import MetadataMigrationManager, MetadataStore
from app.routers.account import router as account_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.components import router as components_router
from app.routers.conversations import router as conversations_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.models import router as models_router
from app.routers.repos import router as repos_router
from app.services.component_registry import ComponentRegistry
from app.services.conversation_service import ConversationPersistenceService
from app.services.document_service import DocumentService
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
    )
    component_registry = ComponentRegistry(
        ollama_service=model_manager.ollama_service,
        vector_store_manager=vector_store_manager,
    )
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
    context_compression_manager = ContextCompressionManager(
        llm_provider=llm_provider,
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
        application.state.metadata_store = metadata_store
        application.state.metadata_migration_manager = metadata_migration_manager
        application.state.metadata_migration_result = (
            metadata_migration_manager.migrate()
        )
        application.state.model_manager = model_manager
        application.state.component_registry = component_registry
        application.state.document_service = document_service
        application.state.conversation_service = conversation_service
        application.state.vector_store_manager = vector_store_manager
        application.state.vector_store = vector_store
        application.state.ai_settings_resolver = ai_settings_resolver
        application.state.llm_provider = llm_provider
        application.state.embedder_provider = embedder_provider
        application.state.reranker_provider = reranker_provider
        application.state.retrieval_pipeline = retrieval_pipeline
        application.state.context_compression_manager = context_compression_manager
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
    application.state.metadata_store = metadata_store
    application.state.metadata_migration_manager = metadata_migration_manager
    application.state.metadata_migration_result = None
    application.state.model_manager = model_manager
    application.state.component_registry = component_registry
    application.state.document_service = document_service
    application.state.conversation_service = conversation_service
    application.state.vector_store_manager = vector_store_manager
    application.state.vector_store = vector_store
    application.state.ai_settings_resolver = ai_settings_resolver
    application.state.llm_provider = llm_provider
    application.state.embedder_provider = embedder_provider
    application.state.reranker_provider = reranker_provider
    application.state.retrieval_pipeline = retrieval_pipeline
    application.state.context_compression_manager = context_compression_manager

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_origin_regex=app_settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(account_router)
    application.include_router(models_router)
    application.include_router(components_router)
    application.include_router(conversations_router)
    application.include_router(documents_router)
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

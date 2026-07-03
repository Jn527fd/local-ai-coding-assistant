from dataclasses import dataclass, replace
import base64
import binascii
from collections.abc import AsyncIterator
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.ai.components import (
    ComponentUnavailableError,
    ContextCompressor,
    EmbedderProvider,
    Reranker,
)
from app.ai.compressors import (
    CompressionInput,
    ContextCompressionManager,
    build_compression_options,
)
from app.ai.execution_context import AISettingsResolver
from app.ai.pipelines import DocumentRetrievalPipeline, RetrievedSource
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.providers import OllamaLLMProvider
from app.ai.rerankers import OllamaRerankerProvider
from app.ai.vectorstores import JsonVectorStore
from app.auth.api_key import require_api_key
from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.component_registry import ComponentRegistry
from app.services.model_manager import (
    ModelManager,
)
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

logger = logging.getLogger(__name__)

RAG_RETRIEVAL_PIPELINES = {"hybrid", "reranked", "graph", "agentic"}
DISABLED_RERANKERS = {"", "none"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
)


@dataclass(frozen=True)
class ChatPrompt:
    text: str
    included_history_messages: int
    retrieved_source_count: int = 0
    memory_summary_used: bool = False


@dataclass(frozen=True)
class RerankPlan:
    should_rerank: bool
    model: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreparedChatExecution:
    execution_context: object
    prompt: ChatPrompt
    prompt_request: ChatRequest
    generation_model: str
    image_payloads: list[str]
    vision_used: bool
    rag_used: bool
    rag_warnings: list[str]
    reranking_used: bool
    reranker_model: str | None
    rerank_warnings: list[str]
    compression_used: bool
    compressor_mode: str
    compression_warnings: list[str]
    compression_stats: dict[str, object]
    retrieved_sources: list[RetrievedSource]
    include_sources: bool

    def generation_settings(self) -> dict[str, object]:
        return {
            "model": self.generation_model,
            "images": self.image_payloads,
            "visionUsed": self.vision_used,
            "executionContext": self.execution_context,
            "retrievedSources": [
                source.response_payload()
                for source in self.retrieved_sources
            ],
        }


def build_retrieved_context_block(
    sources: list[RetrievedSource],
    max_chars: int,
) -> str:
    """Format retrieved chunks for prompt injection within a size limit."""

    if not sources or max_chars <= 0:
        return ""

    lines = [
        "[Retrieved Context]",
        (
            "Use these document excerpts only when relevant. Cite supporting "
            "facts with [Source N]. If the excerpts do not contain the answer, "
            "say so and answer from the conversation normally."
        ),
    ]
    used_chars = sum(len(line) + 1 for line in lines)

    for source in sources:
        entry_header = [
            "",
            f"Source {source.source_number}",
            f"Document: {source.document_name}",
            f"Chunk: {source.chunk_index} ({source.chunk_id})",
            f"Score: {source.score:.3f}",
            "Text:",
        ]
        header_cost = sum(len(line) + 1 for line in entry_header)
        remaining = max_chars - used_chars - header_cost
        if remaining <= 40:
            break

        text = source.text.strip()
        if len(text) > remaining:
            text = f"{text[: max(0, remaining - 14)].rstrip()} [truncated]"

        lines.extend(entry_header)
        lines.append(text)
        used_chars += header_cost + len(text) + 1

    return "\n".join(lines)


def build_memory_block(memory_summary: str | None, max_chars: int) -> str:
    if not memory_summary or max_chars <= 0:
        return ""

    summary = memory_summary.strip()
    if len(summary) > max_chars:
        summary = f"{summary[: max(0, max_chars - 14)].rstrip()} [truncated]"
    return (
        "[Conversation Memory]\n"
        "Use this compressed memory as background context. The latest user "
        "message below remains authoritative.\n"
        f"{summary}"
    )


def _build_conversation_prompt(
    chat_request: ChatRequest,
    max_chars: int,
    force_dialog: bool = False,
) -> ChatPrompt:
    """Build a recent-context prompt that stays within a bounded size."""

    if not chat_request.history:
        if force_dialog:
            prefix = "User: "
            suffix = "\nAssistant:"
            available_chars = max(0, max_chars - len(prefix) - len(suffix))
            message = chat_request.message
            if len(message) > available_chars:
                message = f"{message[: max(0, available_chars - 14)].rstrip()} [truncated]"
            return ChatPrompt(
                text=f"{prefix}{message}{suffix}",
                included_history_messages=0,
            )
        return ChatPrompt(
            text=chat_request.message,
            included_history_messages=0,
        )

    prefix = (
        "Continue the conversation below. Follow the latest user request.\n\n"
    )
    suffix = f"\n\nUser: {chat_request.message}\nAssistant:"
    available_chars = max(0, max_chars - len(prefix) - len(suffix))
    selected_lines: list[str] = []

    for item in reversed(chat_request.history):
        role = "User" if item.role == "user" else "Assistant"
        line = f"{role}: {item.content}"
        line_cost = len(line) + (1 if selected_lines else 0)

        if line_cost <= available_chars:
            selected_lines.append(line)
            available_chars -= line_cost
            continue

        if not selected_lines and available_chars > len(role) + 20:
            marker = "\n[message truncated]"
            content_chars = available_chars - len(role) - 2 - len(marker)
            selected_lines.append(
                f"{role}: {item.content[:content_chars]}{marker}"
            )
        break

    selected_lines.reverse()
    text = prefix + "\n".join(selected_lines) + suffix
    return ChatPrompt(
        text=text,
        included_history_messages=len(selected_lines),
    )


def build_chat_prompt(
    chat_request: ChatRequest,
    max_chars: int,
    retrieved_sources: list[RetrievedSource] | None = None,
    memory_summary: str | None = None,
) -> ChatPrompt:
    """Build the final chat prompt, optionally prefixed with document context."""

    sources = retrieved_sources or []
    if not sources and not memory_summary:
        return _build_conversation_prompt(chat_request, max_chars)

    context_limit = min(6_000, max(0, max_chars // 2))
    context_block = (
        build_retrieved_context_block(
            sources=sources,
            max_chars=context_limit,
        )
        if sources
        else ""
    )
    memory_limit = min(2_500, max(0, max_chars // 4))
    memory_block = build_memory_block(memory_summary, memory_limit)
    blocks = [block for block in (context_block, memory_block) if block]
    if not blocks:
        return _build_conversation_prompt(chat_request, max_chars)

    blocks_text = "\n\n".join(blocks)
    remaining_chars = max(0, max_chars - len(blocks_text) - 2)
    conversation_prompt = _build_conversation_prompt(
        chat_request,
        max_chars=remaining_chars,
        force_dialog=True,
    )
    return ChatPrompt(
        text=f"{blocks_text}\n\n{conversation_prompt.text}",
        included_history_messages=conversation_prompt.included_history_messages,
        retrieved_source_count=len(sources),
        memory_summary_used=bool(memory_block),
    )


def get_ollama_service(request: Request) -> OllamaService:
    """Return the application Ollama client."""

    model_manager: ModelManager = request.app.state.model_manager
    return model_manager.ollama_service


def get_llm_provider(
    request: Request,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> OllamaLLMProvider:
    """Build the chat LLM provider from the request's Ollama client."""

    registered_provider = getattr(request.app.state, "llm_provider", None)
    if getattr(registered_provider, "ollama_service", None) is ollama_service:
        return registered_provider
    return OllamaLLMProvider(ollama_service=ollama_service)


def get_embedder_provider(
    request: Request,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> EmbedderProvider:
    """Return the embedding provider bound to the request's Ollama client."""

    registered_provider = getattr(request.app.state, "embedder_provider", None)
    registered_service = getattr(registered_provider, "ollama_service", None)
    if registered_provider is not None and (
        registered_service is None or registered_service is ollama_service
    ):
        return registered_provider
    return OllamaEmbedderProvider(ollama_service=ollama_service)


def get_reranker_provider(
    request: Request,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> Reranker:
    """Return the reranker provider bound to the request's Ollama client."""

    registered_provider = getattr(request.app.state, "reranker_provider", None)
    registered_service = getattr(registered_provider, "ollama_service", None)
    if registered_provider is not None and (
        registered_service is None or registered_service is ollama_service
    ):
        return registered_provider
    return OllamaRerankerProvider(ollama_service=ollama_service)


def get_context_compression_manager(
    request: Request,
    llm_provider: Annotated[OllamaLLMProvider, Depends(get_llm_provider)],
) -> ContextCompressor:
    """Return the context compression manager for the active LLM provider."""

    registered_manager = getattr(
        request.app.state,
        "context_compression_manager",
        None,
    )
    if getattr(registered_manager, "llm_provider", None) is llm_provider:
        return registered_manager
    return ContextCompressionManager(llm_provider=llm_provider)


def get_vector_store(request: Request) -> JsonVectorStore:
    """Return the configured local vector store."""

    return request.app.state.vector_store


def get_retrieval_pipeline(
    request: Request,
    embedder_provider: Annotated[EmbedderProvider, Depends(get_embedder_provider)],
    vector_store: Annotated[JsonVectorStore, Depends(get_vector_store)],
) -> DocumentRetrievalPipeline:
    """Return a retrieval pipeline for the current providers."""

    registered_pipeline = getattr(request.app.state, "retrieval_pipeline", None)
    if (
        getattr(registered_pipeline, "embedder_provider", None)
        is embedder_provider
        and getattr(registered_pipeline, "vector_store", None) is vector_store
    ):
        return registered_pipeline
    return DocumentRetrievalPipeline(
        embedder_provider=embedder_provider,
        vector_store=vector_store,
    )


def get_ai_settings_resolver(
    request: Request,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> AISettingsResolver:
    """Return a resolver bound to the same Ollama client used for chat."""

    registered_resolver = getattr(
        request.app.state,
        "ai_settings_resolver",
        None,
    )
    registered_registry = getattr(
        registered_resolver,
        "component_registry",
        None,
    )
    registered_service = getattr(registered_registry, "ollama_service", None)
    if registered_resolver is not None and (
        registered_service is None or registered_service is ollama_service
    ):
        return registered_resolver
    return AISettingsResolver(
        component_registry=ComponentRegistry(ollama_service=ollama_service),
    )


def build_rerank_plan(execution_context: object) -> RerankPlan:
    """Return whether this request should rerank vector candidates."""

    reranker_component = execution_context.components["reranker"]
    requested_id = (reranker_component.requested_id or "").strip()
    if requested_id in DISABLED_RERANKERS:
        return RerankPlan(should_rerank=False)

    reranker_model = (execution_context.resolved_reranker or "").strip()
    if (
        reranker_model in DISABLED_RERANKERS
        or not reranker_component.valid
        or not reranker_component.available
    ):
        reason = reranker_component.reason or "reranker is unavailable"
        return RerankPlan(
            should_rerank=False,
            warnings=(
                "Reranking was not used because selected reranker "
                f"'{requested_id}' is unavailable: {reason}.",
            ),
        )

    return RerankPlan(should_rerank=True, model=reranker_model)


def should_attempt_retrieval(
    chat_request: ChatRequest,
    execution_context: object,
) -> bool:
    """Return whether this chat should try vector retrieval."""

    if chat_request.ragOptions and chat_request.ragOptions.enabled is False:
        return False
    reranker_component = execution_context.components["reranker"]
    reranker_requested = (
        reranker_component.requested_id or ""
    ).strip() not in DISABLED_RERANKERS
    return (
        execution_context.resolved_rag_pipeline in RAG_RETRIEVAL_PIPELINES
        or reranker_requested
    )


def rank_sources(
    sources: list[RetrievedSource],
    top_k: int,
) -> list[RetrievedSource]:
    """Assign final source numbers after vector search or reranking."""

    ranked_sources: list[RetrievedSource] = []
    for index, source in enumerate(sources[:top_k], start=1):
        final_score = (
            source.rerank_score
            if source.rerank_score is not None
            else source.vector_score
        )
        ranked_sources.append(
            replace(
                source,
                source_number=index,
                final_rank=index,
                score=final_score,
            )
        )
    return ranked_sources


def prepare_vision_images(chat_request: ChatRequest) -> list[str]:
    """Validate image attachments and return Ollama-ready base64 payloads."""

    prepared_images: list[str] = []
    for image in chat_request.images:
        try:
            decoded = base64.b64decode(image.data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image attachment '{image.name}' is not valid base64.",
            ) from exc

        if not decoded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image attachment '{image.name}' is empty.",
            )
        if len(decoded) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Image attachment '{image.name}' exceeds the "
                    f"{MAX_IMAGE_BYTES // (1024 * 1024)} MiB limit."
                ),
            )
        prepared_images.append(image.data)
    return prepared_images


def resolve_generation_model(
    chat_request: ChatRequest,
    execution_context: object,
) -> tuple[str, bool]:
    """Select the text or vision model for this chat request."""

    if not chat_request.images:
        return execution_context.resolved_llm_model, False

    vision_component = execution_context.components["visionModel"]
    requested_id = (vision_component.requested_id or "").strip()
    vision_model = (execution_context.resolved_vision_model or "").strip()
    if (
        not vision_model
        or vision_model in DISABLED_RERANKERS
        or not vision_component.valid
        or not vision_component.available
    ):
        reason = vision_component.reason or "vision model is unavailable"
        selected = requested_id or "none"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Image chat requires a valid available vision model. "
                f"Selected vision model '{selected}' cannot be used: {reason}."
            ),
        )
    return vision_model, True


async def prepare_chat_execution(
    chat_request: ChatRequest,
    request: Request,
    settings_resolver: AISettingsResolver,
    retrieval_pipeline: DocumentRetrievalPipeline,
    reranker_provider: Reranker,
    compression_manager: ContextCompressor,
) -> PreparedChatExecution:
    """Resolve settings, retrieval, reranking, compression, and prompt."""

    model_manager: ModelManager = request.app.state.model_manager
    if model_manager.is_switching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model switching is in progress. Try again when it completes.",
        )

    active_model = model_manager.active_model
    execution_context = await settings_resolver.resolve(
        conversation_settings=chat_request.conversationSettings,
        active_model=active_model,
        conversation_id=chat_request.conversationId,
    )
    image_payloads = prepare_vision_images(chat_request)
    generation_model, vision_used = resolve_generation_model(
        chat_request,
        execution_context,
    )

    if chat_request.model is not None and chat_request.model != generation_model:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{chat_request.model} is not selected for this request. "
                "Switch models from the account panel or conversation "
                "settings before using it."
            ),
        )

    settings: Settings = request.app.state.settings
    rag_result = None
    rag_options = chat_request.ragOptions
    requested_top_k = rag_options.topK if rag_options else settings.rag_top_k
    top_k = max(1, min(requested_top_k, settings.rag_max_top_k))
    rerank_plan = build_rerank_plan(execution_context)
    candidate_k = top_k
    if rerank_plan.should_rerank:
        requested_candidate_k = (
            rag_options.candidateK if rag_options else settings.rag_candidate_k
        )
        candidate_k = max(
            top_k,
            min(requested_candidate_k, settings.reranker_max_candidates),
        )

    if should_attempt_retrieval(chat_request, execution_context):
        rag_result = await retrieval_pipeline.retrieve(
            query=chat_request.message,
            conversation_id=chat_request.conversationId,
            execution_context=execution_context,
            top_k=candidate_k,
            document_ids=rag_options.documentIds if rag_options else None,
        )

    rag_warnings = list(rag_result.warnings if rag_result else [])
    rerank_warnings = list(rerank_plan.warnings)
    reranking_used = False
    reranker_model = rerank_plan.model
    retrieved_sources = rank_sources(
        rag_result.sources if rag_result else [],
        top_k=top_k,
    )

    if rerank_warnings:
        rag_warnings.extend(rerank_warnings)

    if rag_result and rag_result.rag_used and rerank_plan.should_rerank:
        try:
            rerank_result = await reranker_provider.rerank(
                query=chat_request.message,
                candidate_chunks=rag_result.sources,
                model=rerank_plan.model or "",
                settings={
                    "topK": top_k,
                    "candidateK": candidate_k,
                    "maxPassageChars": 2_000,
                },
            )
            rerank_warnings.extend(rerank_result.warnings)
            rag_warnings.extend(rerank_result.warnings)
            retrieved_sources = rank_sources(rerank_result.sources, top_k=top_k)
            reranking_used = True
        except Exception as exc:
            logger.warning("Reranking failed: %s", exc)
            warning = (
                "Reranking was not used because the selected reranker failed; "
                "using vector-ranked document context."
            )
            rerank_warnings.append(warning)
            rag_warnings.append(warning)
            retrieved_sources = rank_sources(
                rag_result.sources,
                top_k=top_k,
            )

    compression_result = await compression_manager.compress(
        CompressionInput(
            history=chat_request.history,
            latest_user_message=chat_request.message,
            retrieved_sources=retrieved_sources,
            execution_context=execution_context,
            options=build_compression_options(settings),
            model=generation_model,
        )
    )
    prompt_request = chat_request.model_copy(
        update={"history": compression_result.history}
    )
    retrieved_sources = compression_result.retrieved_sources
    prompt = build_chat_prompt(
        prompt_request,
        max_chars=settings.chat_context_max_chars,
        retrieved_sources=retrieved_sources,
        memory_summary=compression_result.memory_summary,
    )
    logger.info(
        (
            "Prepared chat model=%s prompt_chars=%d history_messages=%d/%d "
            "retrieved_sources=%d reranking_used=%s compression_used=%s"
        ),
        generation_model,
        len(prompt.text),
        prompt.included_history_messages,
        len(chat_request.history),
        prompt.retrieved_source_count,
        reranking_used,
        compression_result.compression_used,
    )

    include_sources = rag_options.includeSources if rag_options else True
    return PreparedChatExecution(
        execution_context=execution_context,
        prompt=prompt,
        prompt_request=prompt_request,
        generation_model=generation_model,
        image_payloads=image_payloads,
        vision_used=vision_used,
        rag_used=bool(rag_result and rag_result.rag_used),
        rag_warnings=rag_warnings,
        reranking_used=reranking_used,
        reranker_model=reranker_model if reranking_used else None,
        rerank_warnings=rerank_warnings,
        compression_used=compression_result.compression_used,
        compressor_mode=compression_result.compressor_mode,
        compression_warnings=compression_result.warnings,
        compression_stats=compression_result.stats.response_payload(),
        retrieved_sources=retrieved_sources,
        include_sources=include_sources,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    request: Request,
    llm_provider: Annotated[OllamaLLMProvider, Depends(get_llm_provider)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    retrieval_pipeline: Annotated[
        DocumentRetrievalPipeline,
        Depends(get_retrieval_pipeline),
    ],
    reranker_provider: Annotated[Reranker, Depends(get_reranker_provider)],
    compression_manager: Annotated[
        ContextCompressor,
        Depends(get_context_compression_manager),
    ],
) -> ChatResponse:
    """Send an authenticated chat prompt to the configured Ollama server."""

    model_manager: ModelManager = request.app.state.model_manager
    if model_manager.is_switching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model switching is in progress. Try again when it completes.",
        )

    active_model = model_manager.active_model
    execution_context = await settings_resolver.resolve(
        conversation_settings=chat_request.conversationSettings,
        active_model=active_model,
        conversation_id=chat_request.conversationId,
    )
    image_payloads = prepare_vision_images(chat_request)
    generation_model, vision_used = resolve_generation_model(
        chat_request,
        execution_context,
    )

    if chat_request.model is not None:
        if chat_request.model != generation_model:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{chat_request.model} is not selected for this request. "
                    "Switch models from the account panel or conversation "
                    "settings before using it."
                ),
            )

    settings: Settings = request.app.state.settings
    rag_result = None
    rag_options = chat_request.ragOptions
    requested_top_k = rag_options.topK if rag_options else settings.rag_top_k
    top_k = max(1, min(requested_top_k, settings.rag_max_top_k))
    rerank_plan = build_rerank_plan(execution_context)
    candidate_k = top_k
    if rerank_plan.should_rerank:
        requested_candidate_k = (
            rag_options.candidateK if rag_options else settings.rag_candidate_k
        )
        candidate_k = max(
            top_k,
            min(requested_candidate_k, settings.reranker_max_candidates),
        )

    if should_attempt_retrieval(
        chat_request,
        execution_context,
    ):
        rag_result = await retrieval_pipeline.retrieve(
            query=chat_request.message,
            conversation_id=chat_request.conversationId,
            execution_context=execution_context,
            top_k=candidate_k,
            document_ids=rag_options.documentIds if rag_options else None,
        )

    rag_warnings = list(rag_result.warnings if rag_result else [])
    rerank_warnings = list(rerank_plan.warnings)
    reranking_used = False
    reranker_model = rerank_plan.model
    retrieved_sources = rank_sources(
        rag_result.sources if rag_result else [],
        top_k=top_k,
    )

    if rerank_warnings:
        rag_warnings.extend(rerank_warnings)

    if rag_result and rag_result.rag_used and rerank_plan.should_rerank:
        try:
            rerank_result = await reranker_provider.rerank(
                query=chat_request.message,
                candidate_chunks=rag_result.sources,
                model=rerank_plan.model or "",
                settings={
                    "topK": top_k,
                    "candidateK": candidate_k,
                    "maxPassageChars": 2_000,
                },
            )
            rerank_warnings.extend(rerank_result.warnings)
            rag_warnings.extend(rerank_result.warnings)
            retrieved_sources = rank_sources(
                rerank_result.sources,
                top_k=top_k,
            )
            reranking_used = True
        except Exception as exc:
            logger.warning("Reranking failed: %s", exc)
            warning = (
                "Reranking was not used because the selected reranker failed; "
                "using vector-ranked document context."
            )
            rerank_warnings.append(warning)
            rag_warnings.append(warning)
            retrieved_sources = rank_sources(
                rag_result.sources,
                top_k=top_k,
            )

    compression_result = await compression_manager.compress(
        CompressionInput(
            history=chat_request.history,
            latest_user_message=chat_request.message,
            retrieved_sources=retrieved_sources,
            execution_context=execution_context,
            options=build_compression_options(settings),
            model=generation_model,
        )
    )
    prompt_request = chat_request.model_copy(
        update={"history": compression_result.history}
    )
    retrieved_sources = compression_result.retrieved_sources
    prompt = build_chat_prompt(
        prompt_request,
        max_chars=settings.chat_context_max_chars,
        retrieved_sources=retrieved_sources,
        memory_summary=compression_result.memory_summary,
    )
    logger.info(
        (
            "Sending chat to Ollama model=%s prompt_chars=%d "
            "history_messages=%d/%d retrieved_sources=%d "
            "reranking_used=%s compression_used=%s"
        ),
        generation_model,
        len(prompt.text),
        prompt.included_history_messages,
        len(chat_request.history),
        prompt.retrieved_source_count,
        reranking_used,
        compression_result.compression_used,
    )

    try:
        answer = await llm_provider.generate(
            prompt=prompt.text,
            history=[item.model_dump() for item in prompt_request.history],
            settings={
                "model": generation_model,
                "images": image_payloads,
                "visionUsed": vision_used,
                "executionContext": execution_context,
                "retrievedSources": [
                    source.response_payload()
                    for source in retrieved_sources
                ],
            },
        )
    except ComponentUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OllamaTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except OllamaResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    include_sources = (
        chat_request.ragOptions.includeSources
        if chat_request.ragOptions
        else True
    )
    return ChatResponse(
        model=generation_model,
        answer=answer,
        ragUsed=bool(rag_result and rag_result.rag_used),
        ragWarnings=rag_warnings,
        rerankingUsed=reranking_used,
        rerankerModel=reranker_model if reranking_used else None,
        rerankWarnings=rerank_warnings,
        compressionUsed=compression_result.compression_used,
        compressorMode=compression_result.compressor_mode,
        compressionWarnings=compression_result.warnings,
        compressionStats=compression_result.stats.response_payload(),
        visionUsed=vision_used,
        visionModel=generation_model if vision_used else None,
        sources=(
            [source.response_payload() for source in retrieved_sources]
            if include_sources
            else []
        ),
    )


def _sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chat_metadata_payload(
    prepared: PreparedChatExecution,
) -> dict[str, object]:
    return {
        "model": prepared.generation_model,
        "ragUsed": prepared.rag_used,
        "ragWarnings": prepared.rag_warnings,
        "rerankingUsed": prepared.reranking_used,
        "rerankerModel": prepared.reranker_model,
        "rerankWarnings": prepared.rerank_warnings,
        "compressionUsed": prepared.compression_used,
        "compressorMode": prepared.compressor_mode,
        "compressionWarnings": prepared.compression_warnings,
        "compressionStats": prepared.compression_stats,
        "visionUsed": prepared.vision_used,
        "visionModel": (
            prepared.generation_model if prepared.vision_used else None
        ),
        "visionWarnings": [],
        "sources": (
            [source.response_payload() for source in prepared.retrieved_sources]
            if prepared.include_sources
            else []
        ),
    }


def _stream_error_payload(exc: Exception) -> dict[str, object]:
    if isinstance(exc, ComponentUnavailableError | OllamaUnavailableError):
        return {"status": 503, "message": str(exc)}
    if isinstance(exc, OllamaTimeoutError):
        return {"status": 504, "message": str(exc)}
    if isinstance(exc, OllamaResponseError):
        return {"status": 502, "message": str(exc)}
    logger.exception("Streaming chat failed unexpectedly")
    return {
        "status": 500,
        "message": "Streaming generation failed unexpectedly.",
    }


@router.post("/stream")
async def chat_stream(
    chat_request: ChatRequest,
    request: Request,
    llm_provider: Annotated[OllamaLLMProvider, Depends(get_llm_provider)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    retrieval_pipeline: Annotated[
        DocumentRetrievalPipeline,
        Depends(get_retrieval_pipeline),
    ],
    reranker_provider: Annotated[Reranker, Depends(get_reranker_provider)],
    compression_manager: Annotated[
        ContextCompressor,
        Depends(get_context_compression_manager),
    ],
) -> StreamingResponse:
    """Stream an authenticated chat response as server-sent events."""

    prepared = await prepare_chat_execution(
        chat_request=chat_request,
        request=request,
        settings_resolver=settings_resolver,
        retrieval_pipeline=retrieval_pipeline,
        reranker_provider=reranker_provider,
        compression_manager=compression_manager,
    )

    async def event_stream() -> AsyncIterator[str]:
        yield _sse_event("progress", {"stage": "generating"})
        yield _sse_event("metadata", _chat_metadata_payload(prepared))

        answer_parts: list[str] = []
        try:
            async for chunk in llm_provider.stream_generate(
                prompt=prepared.prompt.text,
                history=[
                    item.model_dump() for item in prepared.prompt_request.history
                ],
                settings=prepared.generation_settings(),
            ):
                answer_parts.append(chunk)
                yield _sse_event("token", {"text": chunk})
        except Exception as exc:
            yield _sse_event("error", _stream_error_payload(exc))
            return

        yield _sse_event(
            "done",
            {
                **_chat_metadata_payload(prepared),
                "answer": "".join(answer_parts).strip(),
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

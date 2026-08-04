from dataclasses import dataclass, replace
import base64
import binascii
from collections.abc import AsyncIterator
import hashlib
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

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
from app.ai.pipelines import (
    DocumentRetrievalPipeline,
    RetrievalResult,
    RetrievedSource,
)
from app.ai.output_sanitizer import ReasoningStreamFilter, strip_reasoning_text
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.providers import OllamaLLMProvider
from app.ai.rerankers import OllamaRerankerProvider
from app.ai.vectorstores import JsonVectorStore
from app.auth.api_key import require_session_or_api_key
from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.component_registry import ComponentRegistry
from app.services.model_manager import (
    ModelManager,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    DocumentValidationError,
)
from app.services.conversation_memory import ConversationMemoryService
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
SEMANTIC_RAG_MIN_SCORE = 0.15
SMALL_DOCUMENT_CONTEXT_MAX_CHARS = 6_000
IMAGE_BASED_PDF_LIMITED_TEXT_MESSAGE = (
    "I found the uploaded PDF, but most of its content appears to be "
    "image-based and OCR is not available, so I can only read limited "
    "embedded text."
)
DOCUMENT_ACCESS_REFUSAL_MARKERS = (
    "cannot access the file",
    "can't access the file",
    "cannot access this file",
    "can't access this file",
    "cannot access the document",
    "can't access the document",
    "do not have access to the file",
    "don't have access to the file",
    "do not have access to the document",
    "don't have access to the document",
    "unable to access the file",
    "unable to access the document",
    "cannot view the contents",
    "can't view the contents",
    "please ensure it's attached",
    "please ensure it is attached",
    "attached to your current message",
    "attach the document",
    "attach the file",
    "upload the document",
    "re-upload the document",
    "reupload the document",
    "need access to the full text",
    "need the full text",
    "would need access to the full text",
    "document is incomplete",
    "chunks were truncated",
    "chunk was truncated",
    "text for chunks",
    "text for chunk",
    "were truncated",
    "was truncated",
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_session_or_api_key)],
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
class DocumentContextSelection:
    mode: str
    selected_document_ids: list[str]
    retrieval_result: RetrievalResult | None = None
    confidence: float = 0.0
    reason: str = ""
    broader_retrieval_used: bool = False
    debug_metadata: dict[str, object] | None = None


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
    memory_store_warnings: list[str]
    limited_document_text_warning: str = ""

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
    attachment_document_ids: list[str] | None = None,
    broader_retrieval_used: bool = False,
    retrieval_mode: str = "",
) -> str:
    """Format retrieved chunks for prompt injection within a size limit."""

    if not sources or max_chars <= 0:
        return ""

    attachment_ids = set(attachment_document_ids or [])
    lines = [
        "<document_context>",
        (
            "The following excerpts were retrieved from files attached to this "
            "conversation. Use them to answer the user's question. If the "
            "excerpts are insufficient, say what is missing. Do not claim you "
            "cannot access the file when excerpts are present."
        ),
        (
            "Runtime instruction: answer using document_context, mention the "
            "document's actual contents, and cite or reference source names "
            "and pages when available. Do not ask the user to re-upload or "
            "attach the file while document_context is present."
        ),
        (
            "Document excerpts may be partial. Answer the user's question using "
            "the provided excerpts. Do not complain that chunks are partial or "
            "shortened. Only say information is missing if the excerpts truly "
            "do not contain the answer."
        ),
        f"Retrieval mode: {retrieval_mode or 'semantic_rag'}",
    ]
    if attachment_ids:
        lines.append(
            (
                "The user attached document(s) to the current message. For "
                "references like 'this document', 'this PDF', or 'the attached "
                "file', answer from the current message attachments first. Do "
                "not use older conversation documents unless the user explicitly "
                "asks to compare or reference previous uploads."
            )
        )
    else:
        lines.append(
            (
                "Use these document excerpts only when relevant. Cite supporting "
                "facts with [Source N]. If the excerpts do not contain the answer, "
                "say so and answer from the conversation normally."
            )
        )
    if broader_retrieval_used:
        lines.append(
            (
                "This request appears to ask about previous or multiple uploaded "
                "documents, so historical document excerpts may be included after "
                "the current attachment context."
            )
        )
    used_chars = sum(len(line) + 1 for line in lines)

    for source in sources:
        scope = (
            "current message attachment"
            if source.document_id in attachment_ids
            else "historical conversation document"
        )
        page_label = (
            str(source.page_number)
            if source.page_number is not None
            else "unknown"
        )
        entry_header = [
            "",
            f"Source {source.source_number}: {source.document_name}",
            f"Document ID: {source.document_id}",
            f"Page: {page_label}",
            f"Scope: {scope}",
            f"Chunk: {source.chunk_index} ({source.chunk_id})",
            f"Score: {source.score:.3f}",
            "Text:",
        ]
        header_cost = sum(len(line) + 1 for line in entry_header)
        remaining = max_chars - used_chars - header_cost
        if remaining <= 40:
            break

        text = clean_model_excerpt_text(source.text)
        if len(text) > remaining:
            text = clean_model_excerpt_text(text[:remaining])

        lines.extend(entry_header)
        lines.append(text)
        used_chars += header_cost + len(text) + 1

    lines.append("</document_context>")
    return "\n".join(lines)


def clean_model_excerpt_text(text: str) -> str:
    cleaned = text.strip()
    while cleaned.endswith("[truncated]"):
        cleaned = cleaned[: -len("[truncated]")].rstrip()
    return cleaned


def looks_like_document_access_refusal(answer: str) -> bool:
    normalized = " ".join(answer.lower().split())
    return any(marker in normalized for marker in DOCUMENT_ACCESS_REFUSAL_MARKERS)


def build_document_context_fallback_answer(
    sources: list[RetrievedSource],
    max_sources: int = 3,
    max_excerpt_chars: int = 700,
) -> str:
    excerpts: list[str] = []
    for source in sources[:max_sources]:
        text = " ".join(source.text.split())
        text = clean_model_excerpt_text(text)
        if not text:
            continue
        if len(text) > max_excerpt_chars:
            text = clean_model_excerpt_text(text[:max_excerpt_chars])
        page = (
            f", page {source.page_number}"
            if source.page_number is not None
            else ""
        )
        excerpts.append(f"- {source.document_name}{page}: {text}")

    if not excerpts:
        return (
            "I found document context for this conversation, but the retrieved "
            "chunks did not contain readable text."
        )
    return (
        "I found readable text in the uploaded document context. Relevant "
        "excerpt(s):\n"
        + "\n".join(excerpts)
    )


def repair_document_access_refusal(
    answer: str,
    retrieved_sources: list[RetrievedSource],
) -> str:
    if not retrieved_sources or not looks_like_document_access_refusal(answer):
        return answer
    logger.info(
        "Replacing document access refusal with retrieved context excerpt answer."
    )
    return build_document_context_fallback_answer(retrieved_sources)


def image_based_pdf_limited_text_warning(
    documents: list[dict[str, object]],
) -> str:
    for document in documents:
        diagnostics = document.get("extractionDiagnostics")
        if not isinstance(diagnostics, dict):
            continue
        extension = str(document.get("extension") or "").lower()
        ocr_engine = str(document.get("resolvedOcrEngine") or "none").lower()
        if (
            extension == ".pdf"
            and ocr_engine == "none"
            and (
                diagnostics.get("ocrNeeded") is True
                or diagnostics.get("likelyImageBased") is True
            )
        ):
            return IMAGE_BASED_PDF_LIMITED_TEXT_MESSAGE
    return ""


def prepend_limited_document_warning(answer: str, warning: str) -> str:
    if not warning:
        return answer
    if warning.lower() in answer.lower():
        return answer
    return f"{warning}\n\n{answer}" if answer else warning


def log_document_context_debug(
    conversation_id: str | None,
    query: str,
    selection: DocumentContextSelection,
    retrieved_sources: list[RetrievedSource],
    document_context_included: bool,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug(
        (
            "Document context debug conversation_id=%s mode=%s reason=%s "
            "active_document_ids=%s retrieval_query=%r chunks_retrieved=%d "
            "document_context_included=%s"
        ),
        conversation_id,
        selection.mode,
        selection.reason,
        selection.selected_document_ids,
        query,
        len(retrieved_sources),
        document_context_included,
    )
    for source in retrieved_sources:
        preview = " ".join(source.text.split())[:200]
        logger.debug(
            (
                "Retrieved document chunk document_id=%s filename=%s "
                "chunk_id=%s page=%s preview=%r"
            ),
            source.document_id,
            source.document_name,
            source.chunk_id,
            source.page_number,
            preview,
        )


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


def build_system_prompt_block(system_prompt: str | None, max_chars: int) -> str:
    if not system_prompt or max_chars <= 0:
        return ""

    instructions = system_prompt.strip()
    if not instructions:
        return ""
    if len(instructions) > max_chars:
        instructions = (
            f"{instructions[: max(0, max_chars - 14)].rstrip()} [truncated]"
        )
    return (
        "[System Instructions]\n"
        "Follow these conversation-specific instructions unless they conflict "
        "with higher-priority safety or runtime instructions.\n"
        f"{instructions}"
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
    attachment_document_ids: list[str] | None = None,
    broader_retrieval_used: bool = False,
    retrieval_mode: str = "",
) -> ChatPrompt:
    """Build the final chat prompt, optionally prefixed with document context."""

    sources = retrieved_sources or []
    system_limit = min(4_000, max(0, max_chars // 3))
    system_block = build_system_prompt_block(
        chat_request.systemPrompt,
        system_limit,
    )
    if not sources and not memory_summary and not system_block:
        return _build_conversation_prompt(chat_request, max_chars)

    context_limit = min(6_000, max(0, max_chars // 2))
    context_block = (
        build_retrieved_context_block(
            sources=sources,
            max_chars=context_limit,
            attachment_document_ids=attachment_document_ids,
            broader_retrieval_used=broader_retrieval_used,
            retrieval_mode=retrieval_mode,
        )
        if sources
        else ""
    )
    memory_limit = min(2_500, max(0, max_chars // 4))
    memory_block = build_memory_block(memory_summary, memory_limit)
    blocks = [
        block for block in (system_block, context_block, memory_block) if block
    ]
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


def get_conversation_memory_service(
    request: Request,
    embedder_provider: Annotated[EmbedderProvider, Depends(get_embedder_provider)],
) -> ConversationMemoryService:
    """Return the separate long-term conversation memory service."""

    registered_service = request.app.state.conversation_memory_service
    if getattr(registered_service, "embedder_provider", None) is embedder_provider:
        return registered_service
    settings: Settings = request.app.state.settings
    return ConversationMemoryService(
        vector_store=request.app.state.vector_store_manager.qdrant_store,
        embedder_provider=embedder_provider,
        collection_name=settings.memory_collection_name,
        min_importance=settings.memory_min_importance,
    )


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


async def retrieve_conversation_memory_context(
    chat_request: ChatRequest,
    settings: Settings,
    execution_context: object,
    memory_service: ConversationMemoryService,
) -> tuple[str, list[str]]:
    """Retrieve durable long-term memories without touching document RAG."""

    embedder_component = execution_context.components["embedderModel"]
    if not execution_context.resolved_embedder_model or not embedder_component.valid:
        return "", []
    existing = memory_service.list(
        workspace_id="default",
        conversation_id=chat_request.conversationId,
        include_workspace_wide=True,
        limit=1,
    )
    if not existing.memories:
        return "", existing.warnings
    result = await memory_service.retrieve(
        workspace_id="default",
        conversation_id=chat_request.conversationId,
        query=chat_request.message,
        embedder_model=execution_context.resolved_embedder_model,
        top_k=settings.memory_top_k,
        min_importance=settings.memory_min_importance,
        include_workspace_wide=True,
    )
    return memory_service.format_memory_context(result.memories), result.warnings


async def store_durable_memory_from_chat(
    chat_request: ChatRequest,
    settings: Settings,
    execution_context: object,
    memory_service: ConversationMemoryService,
) -> None:
    """Persist durable user-provided facts/preferences for future turns."""

    if not settings.memory_auto_store_enabled:
        return
    source_hash = hashlib.sha256(chat_request.message.encode("utf-8")).hexdigest()[:16]
    try:
        result = await memory_service.store_from_message(
            workspace_id="default",
            conversation_id=chat_request.conversationId,
            message=chat_request.message,
            source_message_id=f"latest-user:{source_hash}",
            source_role="user",
            embedder_model=execution_context.resolved_embedder_model,
            enabled=True,
        )
    except Exception as exc:
        logger.warning("Durable conversation memory storage failed: %s", exc)
        return
    for warning in result.warnings:
        logger.info("Durable conversation memory not stored: %s", warning)


def should_attempt_retrieval(
    chat_request: ChatRequest,
    execution_context: object,
) -> bool:
    """Return whether this chat should try vector retrieval."""

    if chat_request.ragOptions and chat_request.ragOptions.enabled is False:
        return False
    if requested_document_ids(chat_request):
        return True
    if likely_document_retrieval_query(chat_request.message):
        return True
    if chat_request.ragOptions and chat_request.ragOptions.enabled is True:
        return True
    reranker_component = execution_context.components["reranker"]
    reranker_requested = (
        reranker_component.requested_id or ""
    ).strip() not in DISABLED_RERANKERS
    return (
        execution_context.resolved_rag_pipeline in RAG_RETRIEVAL_PIPELINES
        or reranker_requested
    )


def requested_document_ids(chat_request: ChatRequest) -> list[str]:
    """Return unique explicit document IDs requested for this chat."""

    document_ids = current_attachment_document_ids(chat_request)
    if document_ids:
        return document_ids

    if not chat_request.ragOptions:
        return []

    return _unique_document_ids(chat_request.ragOptions.documentIds)


def current_attachment_document_ids(chat_request: ChatRequest) -> list[str]:
    """Return document IDs attached to the current user message."""

    document_ids = _unique_document_ids(chat_request.attachment_document_ids)
    if document_ids:
        return document_ids
    if chat_request.ragOptions:
        return _unique_document_ids(chat_request.ragOptions.documentIds)
    return []


def _unique_document_ids(raw_document_ids: list[str]) -> list[str]:
    document_ids: list[str] = []
    seen: set[str] = set()
    for document_id in raw_document_ids:
        normalized = document_id.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            document_ids.append(normalized)
    return document_ids


def requests_broader_document_context(message: str) -> bool:
    """Detect when the user is asking beyond the current attachment."""

    normalized = " ".join(message.lower().split())
    broader_markers = [
        "compare",
        "previous",
        "earlier",
        "before",
        "both documents",
        "all documents",
        "all my documents",
        "all uploaded",
        "uploaded earlier",
        "previous upload",
        "search all",
        "find this topic",
    ]
    return any(marker in normalized for marker in broader_markers)


def normalize_for_matching(value: object) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").split())


def document_filename_terms(document: dict[str, object]) -> set[str]:
    filename = normalize_for_matching(document.get("originalFilename"))
    stem = filename.rsplit(".", maxsplit=1)[0]
    terms = {
        term
        for term in stem.replace("-", " ").replace(".", " ").split()
        if len(term) >= 3
    }
    return terms


def is_pdf_document(document: dict[str, object]) -> bool:
    filename = normalize_for_matching(document.get("originalFilename"))
    mime_type = normalize_for_matching(document.get("mimeType"))
    extension = normalize_for_matching(document.get("extension"))
    return filename.endswith(".pdf") or mime_type == "application/pdf" or extension == ".pdf"


def is_processed_document(document: dict[str, object]) -> bool:
    return (
        str(document.get("status") or "") == "processed"
        and int(document.get("chunkCount") or 0) > 0
        and bool(document.get("documentId"))
    )


def document_reference_kind(message: str) -> str:
    normalized = normalize_for_matching(message)
    if any(term in normalized for term in ["resume", "cv"]):
        return "resume"
    if any(
        term in normalized
        for term in ["certificate", "certification", "certifications"]
    ):
        return "certificate"
    if "invoice" in normalized:
        return "invoice"
    generic_reference_markers = [
        "this pdf",
        "that pdf",
        "the pdf",
        "this document",
        "that document",
        "the document",
        "this attachment",
        "that attachment",
        "the attachment",
        "attached file",
        "the attached file",
        "this file",
        "that file",
        "the file",
    ]
    if any(marker in normalized for marker in generic_reference_markers):
        return "document"
    if any(
        marker in normalized
        for marker in [
            "uploaded earlier",
            "uploaded before",
            "one i uploaded",
            "that document",
            "that file",
            "what did it say",
            "what was in it",
        ]
    ):
        return "vague"
    return ""


def likely_document_retrieval_query(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if document_reference_kind(normalized):
        return True
    retrieval_markers = [
        "docs",
        "documents",
        "use docs",
        "use documents",
        "what document",
        "document talks",
        "document mentions",
        "what program is mentioned",
        "which program is mentioned",
        "what is mentioned",
        "what does it mention",
        "what did my",
        "what certifications",
        "certifications do i have",
        "expiration date",
        "expire",
        "experience",
        "react",
        "uploaded",
        "in my documents",
        "in the docs",
        "remind me what was in",
    ]
    return any(marker in normalized for marker in retrieval_markers)


def broad_document_overview_query(message: str) -> bool:
    normalized = normalize_for_matching(message)
    overview_markers = [
        "what is in this document",
        "what's in this document",
        "what is in the document",
        "what does this document contain",
        "what does the document contain",
        "what does this contain",
        "what is in this file",
        "what's in this file",
        "what does this file contain",
        "what is in this pdf",
        "what's in this pdf",
        "summarize this pdf",
        "summarize this document",
        "summarize this file",
        "what certificates are in this file",
        "what certificates are in this document",
        "what certificates are in this pdf",
    ]
    return any(marker in normalized for marker in overview_markers)


def has_configured_document_retrieval(execution_context: object) -> bool:
    reranker_component = execution_context.components["reranker"]
    reranker_requested = (
        reranker_component.requested_id or ""
    ).strip() not in DISABLED_RERANKERS
    return (
        execution_context.resolved_rag_pipeline in RAG_RETRIEVAL_PIPELINES
        or reranker_requested
    )


def match_referenced_documents(
    message: str,
    documents: list[dict[str, object]],
) -> tuple[list[str], bool, str]:
    kind = document_reference_kind(message)
    if not kind:
        return [], False, ""

    processed_documents = [document for document in documents if is_processed_document(document)]
    if not processed_documents:
        return [], False, kind

    normalized = normalize_for_matching(message)
    matches: list[dict[str, object]] = []
    if kind == "resume":
        matches = [
            document
            for document in processed_documents
            if "resume" in document_filename_terms(document)
            or "cv" in document_filename_terms(document)
        ]
    elif kind == "certificate":
        matches = [
            document
            for document in processed_documents
            if any(
                term in document_filename_terms(document)
                for term in ["certificate", "certification", "certifications"]
            )
        ]
    elif kind == "invoice":
        matches = [
            document
            for document in processed_documents
            if "invoice" in document_filename_terms(document)
        ]
    elif kind == "document":
        if "pdf" in normalized:
            matches = [document for document in processed_documents if is_pdf_document(document)]
        else:
            matches = processed_documents
    elif kind == "vague":
        matches = processed_documents[:1]

    if not matches:
        return [], False, kind
    if len(matches) > 1 and kind != "vague":
        return [
            str(document.get("documentId"))
            for document in matches
            if document.get("documentId")
        ], True, kind
    return [
        str(document.get("documentId"))
        for document in matches[:1]
        if document.get("documentId")
    ], False, kind


def filter_relevant_sources(
    result: RetrievalResult,
    min_score: float,
) -> RetrievalResult:
    relevant_sources = [
        source
        for source in result.sources
        if float(source.score) >= min_score
    ]
    warnings = list(result.warnings)
    if result.sources and not relevant_sources:
        warnings.append(
            "Document retrieval was skipped because no retrieved chunks met the relevance threshold."
        )
    return RetrievalResult(
        rag_used=bool(relevant_sources),
        warnings=warnings,
        sources=relevant_sources,
    )


async def list_conversation_documents(
    request: Request,
    conversation_id: str | None,
) -> list[dict[str, object]]:
    if not conversation_id:
        return []
    document_service: DocumentService = request.app.state.document_service
    try:
        documents = await run_in_threadpool(
            document_service.list_documents,
            conversation_id,
        )
    except (DocumentValidationError, DocumentStorageError) as exc:
        logger.warning(
            "Could not list conversation documents conversation_id=%s: %s",
            conversation_id,
            exc,
        )
        return []
    return documents


def clarification_detail(
    kind: str,
    document_ids: list[str],
    documents: list[dict[str, object]],
) -> str:
    names_by_id = {
        str(document.get("documentId")): str(document.get("originalFilename") or "Document")
        for document in documents
    }
    names = [
        names_by_id.get(document_id, document_id)
        for document_id in document_ids
    ]
    label = "PDF" if kind == "document" else kind or "document"
    return (
        f"Which {label} do you mean? I found multiple matching uploads: "
        f"{', '.join(names)}."
    )


def merge_retrieval_results(
    attachment_result: RetrievalResult,
    historical_result: RetrievalResult | None,
    attachment_document_ids: list[str],
) -> RetrievalResult:
    if historical_result is None:
        return attachment_result

    attachment_ids = set(attachment_document_ids)
    seen_chunks = {source.chunk_id for source in attachment_result.sources}
    historical_sources = [
        source
        for source in historical_result.sources
        if source.chunk_id not in seen_chunks
        and source.document_id not in attachment_ids
    ]
    return RetrievalResult(
        rag_used=bool(attachment_result.sources or historical_sources),
        warnings=[*attachment_result.warnings, *historical_result.warnings],
        sources=[*attachment_result.sources, *historical_sources],
    )


def coerce_positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def source_preview(text: str, max_chars: int = 280) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 14].rstrip()} [truncated]"


def source_from_stored_chunk(
    raw_chunk: dict[str, Any],
    document: dict[str, object],
    source_number: int,
) -> RetrievedSource | None:
    text = str(raw_chunk.get("text") or "").strip()
    if not text:
        return None
    metadata = (
        raw_chunk.get("metadata")
        if isinstance(raw_chunk.get("metadata"), dict)
        else {}
    )
    document_id = str(
        raw_chunk.get("documentId")
        or document.get("documentId")
        or ""
    )
    document_name = str(document.get("originalFilename") or "Document")
    chunk_index = int(raw_chunk.get("index") or raw_chunk.get("chunkIndex") or 0)
    chunk_id = str(raw_chunk.get("chunkId") or f"{document_id}:{chunk_index}")
    page_number = coerce_positive_int(
        raw_chunk.get("pageNumber")
        or raw_chunk.get("page")
        or metadata.get("pageNumber")
        or metadata.get("page")
        or metadata.get("page_number")
    )
    return RetrievedSource(
        source_number=source_number,
        document_id=document_id,
        document_name=document_name,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        score=1.0,
        vector_score=1.0,
        text=text,
        text_preview=source_preview(text),
        page_number=page_number,
        final_rank=source_number,
        collection_id=None,
    )


async def retrieve_all_attached_document_chunks(
    request: Request,
    conversation_id: str | None,
    document_ids: list[str],
    max_chars: int = SMALL_DOCUMENT_CONTEXT_MAX_CHARS,
) -> RetrievalResult | None:
    if not conversation_id or not document_ids:
        return None

    document_service: DocumentService = request.app.state.document_service
    sources: list[RetrievedSource] = []
    warnings: list[str] = []
    total_chars = 0
    for document_id in document_ids:
        try:
            document = await run_in_threadpool(
                document_service.get_document,
                conversation_id,
                document_id,
            )
            chunks_payload = await run_in_threadpool(
                document_service.get_chunks,
                conversation_id,
                document_id,
            )
        except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
            warnings.append(str(exc))
            continue

        raw_chunks = chunks_payload.get("chunks")
        if not isinstance(raw_chunks, list):
            continue
        for raw_chunk in raw_chunks:
            if not isinstance(raw_chunk, dict):
                continue
            source = source_from_stored_chunk(
                raw_chunk,
                document,
                len(sources) + 1,
            )
            if source is None:
                continue
            total_chars += len(source.text)
            if total_chars > max_chars:
                logger.info(
                    (
                        "Full attachment context skipped because stored chunks "
                        "exceed context budget conversation_id=%s "
                        "document_ids=%s total_chars=%d max_chars=%d"
                    ),
                    conversation_id,
                    document_ids,
                    total_chars,
                    max_chars,
                )
                return None
            sources.append(source)

    if not sources:
        return None
    logger.info(
        (
            "Using full attached document context conversation_id=%s "
            "document_ids=%s chunks=%d total_chars=%d"
        ),
        conversation_id,
        document_ids,
        len(sources),
        total_chars,
    )
    return RetrievalResult(
        rag_used=True,
        warnings=warnings,
        sources=sources,
    )


async def retrieve_document_context(
    chat_request: ChatRequest,
    request: Request,
    execution_context: object,
    retrieval_pipeline: DocumentRetrievalPipeline,
    top_k: int,
    candidate_k: int,
) -> DocumentContextSelection:
    if not should_attempt_retrieval(chat_request, execution_context):
        logger.info(
            "Document context selector mode=none reason=retrieval_not_requested"
        )
        return DocumentContextSelection(
            mode="none",
            selected_document_ids=[],
            reason="retrieval_not_requested",
        )

    attachment_ids = current_attachment_document_ids(chat_request)
    broader_requested = bool(attachment_ids) and requests_broader_document_context(
        chat_request.message
    )
    if attachment_ids:
        if broad_document_overview_query(chat_request.message):
            full_attachment_result = await retrieve_all_attached_document_chunks(
                request=request,
                conversation_id=chat_request.conversationId,
                document_ids=attachment_ids,
            )
            if full_attachment_result and full_attachment_result.sources:
                logger.info(
                    (
                        "Document context selector mode=current_attachment "
                        "reason=full_small_document_context conversation_id=%s "
                        "attachment_ids=%s retrieved_chunks=%d"
                    ),
                    chat_request.conversationId,
                    attachment_ids,
                    len(full_attachment_result.sources),
                )
                return DocumentContextSelection(
                    mode="current_attachment",
                    selected_document_ids=attachment_ids,
                    retrieval_result=full_attachment_result,
                    confidence=1.0,
                    reason="full_small_document_context",
                )

        attachment_result = await retrieval_pipeline.retrieve(
            query=chat_request.message,
            conversation_id=chat_request.conversationId,
            execution_context=execution_context,
            top_k=candidate_k,
            document_ids=attachment_ids,
        )
        if not broader_requested:
            logger.info(
                (
                    "Document context selector mode=current_attachment "
                    "conversation_id=%s attachment_ids=%s retrieved_chunks=%d"
                ),
                chat_request.conversationId,
                attachment_ids,
                len(attachment_result.sources),
            )
            return DocumentContextSelection(
                mode="current_attachment",
                selected_document_ids=attachment_ids,
                retrieval_result=attachment_result,
                confidence=1.0,
                reason="current_message_attachments",
            )

        historical_result = await retrieval_pipeline.retrieve(
            query=chat_request.message,
            conversation_id=chat_request.conversationId,
            execution_context=execution_context,
            top_k=max(candidate_k, top_k),
            document_ids=None,
        )
        merged = merge_retrieval_results(
            attachment_result,
            historical_result,
            attachment_ids,
        )
        logger.info(
            (
                "Document context selector mode=cross_document "
                "conversation_id=%s attachment_ids=%s retrieved_chunks=%d"
            ),
            chat_request.conversationId,
            attachment_ids,
            len(merged.sources),
        )
        return DocumentContextSelection(
            mode="cross_document",
            selected_document_ids=[
                *attachment_ids,
                *[
                    source.document_id
                    for source in historical_result.sources
                    if source.document_id not in attachment_ids
                ],
            ],
            retrieval_result=merged,
            confidence=0.95,
            reason="current_attachment_with_cross_document_request",
            broader_retrieval_used=True,
        )

    documents = await list_conversation_documents(
        request,
        chat_request.conversationId,
    )
    matched_document_ids, ambiguous, reference_kind = match_referenced_documents(
        chat_request.message,
        documents,
    )
    if ambiguous:
        detail = clarification_detail(reference_kind, matched_document_ids, documents)
        logger.info(
            (
                "Document context selector mode=needs_clarification "
                "conversation_id=%s kind=%s matches=%s"
            ),
            chat_request.conversationId,
            reference_kind,
            matched_document_ids,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
    if matched_document_ids:
        result = await retrieval_pipeline.retrieve(
            query=chat_request.message,
            conversation_id=chat_request.conversationId,
            execution_context=execution_context,
            top_k=candidate_k,
            document_ids=matched_document_ids,
        )
        logger.info(
            (
                "Document context selector mode=conversation_reference "
                "conversation_id=%s reference_kind=%s selected_ids=%s retrieved_chunks=%d"
            ),
            chat_request.conversationId,
            reference_kind,
            matched_document_ids,
            len(result.sources),
        )
        if not result.sources:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Referenced document context could not be retrieved. "
                    "Make sure the document finished indexing before asking about it."
                ),
            )
        return DocumentContextSelection(
            mode="conversation_reference",
            selected_document_ids=matched_document_ids,
            retrieval_result=result,
            confidence=0.85,
            reason=f"matched_{reference_kind}_reference",
        )

    if not likely_document_retrieval_query(chat_request.message):
        logger.info(
            (
                "Document context selector mode=none reason=gating_skipped "
                "conversation_id=%s message=%s"
            ),
            chat_request.conversationId,
            chat_request.message,
        )
        return DocumentContextSelection(
            mode="none",
            selected_document_ids=[],
            reason="gating_skipped",
        )

    result = await retrieval_pipeline.retrieve(
        query=chat_request.message,
        conversation_id=chat_request.conversationId,
        execution_context=execution_context,
        top_k=candidate_k,
        document_ids=chat_request.ragOptions.documentIds
        if chat_request.ragOptions
        else None,
    )
    configured_retrieval = (
        has_configured_document_retrieval(execution_context)
        or bool(chat_request.ragOptions and chat_request.ragOptions.enabled is True)
    )
    relevant_result = (
        result
        if configured_retrieval
        else filter_relevant_sources(result, SEMANTIC_RAG_MIN_SCORE)
    )
    logger.info(
        (
            "Document context selector mode=semantic_rag conversation_id=%s "
            "retrieved_chunks=%d relevant_chunks=%d threshold=%.2f "
            "configured_retrieval=%s"
        ),
        chat_request.conversationId,
        len(result.sources),
        len(relevant_result.sources),
        SEMANTIC_RAG_MIN_SCORE,
        configured_retrieval,
    )
    if not relevant_result.sources:
        return DocumentContextSelection(
            mode="none",
            selected_document_ids=[],
            retrieval_result=relevant_result,
            confidence=0.0,
            reason="semantic_rag_below_threshold",
        )
    selected_ids = []
    for source in relevant_result.sources:
        if source.document_id not in selected_ids:
            selected_ids.append(source.document_id)
    return DocumentContextSelection(
        mode="semantic_rag",
        selected_document_ids=selected_ids,
        retrieval_result=relevant_result,
        confidence=max(float(source.score) for source in relevant_result.sources),
        reason="semantic_document_query",
    )


async def resolve_attached_documents(
    chat_request: ChatRequest,
    request: Request,
) -> list[dict[str, object]]:
    """Validate explicit document IDs before building a model prompt."""

    document_ids = requested_document_ids(chat_request)
    if not document_ids:
        return []

    if not chat_request.conversationId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attached documents require a conversationId.",
        )

    document_service: DocumentService = request.app.state.document_service
    documents: list[dict[str, object]] = []
    for document_id in document_ids:
        try:
            document = await run_in_threadpool(
                document_service.get_document,
                chat_request.conversationId,
                document_id,
            )
        except DocumentNotFoundError as exc:
            logger.info(
                "Chat attachment rejected document_id=%s conversation_id=%s reason=not_found",
                document_id,
                chat_request.conversationId,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attached document was not found for this conversation.",
            ) from exc
        except DocumentValidationError as exc:
            logger.info(
                "Chat attachment rejected document_id=%s conversation_id=%s reason=invalid",
                document_id,
                chat_request.conversationId,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except DocumentStorageError as exc:
            logger.warning(
                "Chat attachment storage failure document_id=%s conversation_id=%s: %s",
                document_id,
                chat_request.conversationId,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        status_value = str(document.get("status") or "uploaded")
        chunk_count = int(document.get("chunkCount") or 0)
        char_length = int(
            (
                document.get("extractionDiagnostics")
                if isinstance(document.get("extractionDiagnostics"), dict)
                else {}
            ).get("charLength")
            or 0
        )
        logger.info(
            (
                "Resolved chat attachment document_id=%s conversation_id=%s "
                "status=%s extracted_chars=%d chunks=%d"
            ),
            document_id,
            chat_request.conversationId,
            status_value,
            char_length,
            chunk_count,
        )

        if status_value == "failed":
            filename = str(document.get("originalFilename") or "Document")
            error = str(document.get("error") or "Document processing failed.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Attached document '{filename}' could not be processed: "
                    f"{error}"
                ),
            )
        if status_value != "processed":
            filename = str(document.get("originalFilename") or "Document")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Attached document '{filename}' is still {status_value}. "
                    "Wait for processing to finish before sending it."
                ),
            )
        if chunk_count <= 0:
            filename = str(document.get("originalFilename") or "Document")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Attached document '{filename}' has no extracted chunks "
                    "available for chat."
                ),
            )
        documents.append(document)

    return documents


def ensure_attached_context_was_retrieved(
    chat_request: ChatRequest,
    retrieved_sources: list[RetrievedSource],
    rag_warnings: list[str],
) -> None:
    document_ids = requested_document_ids(chat_request)
    if not document_ids or retrieved_sources:
        return

    warning_suffix = f" {' '.join(rag_warnings)}" if rag_warnings else ""
    logger.info(
        (
            "Attached document retrieval produced no chunks "
            "conversation_id=%s document_ids=%s warnings=%s"
        ),
        chat_request.conversationId,
        document_ids,
        rag_warnings,
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Attached document content could not be retrieved for this message. "
            "Make sure the document finished indexing before sending it."
            f"{warning_suffix}"
        ).strip(),
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
    memory_service: ConversationMemoryService,
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
    attached_documents = await resolve_attached_documents(chat_request, request)
    limited_document_text_warning = image_based_pdf_limited_text_warning(
        attached_documents
    )
    if attached_documents:
        logger.info(
            "Chat request received attachment_ids=%s",
            [document.get("documentId") for document in attached_documents],
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
    context_selection = DocumentContextSelection(
        mode="none",
        selected_document_ids=[],
    )
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

    context_selection = await retrieve_document_context(
        chat_request=chat_request,
        request=request,
        execution_context=execution_context,
        retrieval_pipeline=retrieval_pipeline,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    rag_result = context_selection.retrieval_result

    rag_warnings = list(rag_result.warnings if rag_result else [])
    rerank_warnings = list(rerank_plan.warnings)
    reranking_used = False
    reranker_model = rerank_plan.model
    retrieved_sources = rank_sources(
        rag_result.sources if rag_result else [],
        top_k=top_k,
    )
    ensure_attached_context_was_retrieved(
        chat_request,
        retrieved_sources,
        rag_warnings,
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

    memory_context, memory_warnings = await retrieve_conversation_memory_context(
        chat_request=chat_request,
        settings=settings,
        execution_context=execution_context,
        memory_service=memory_service,
    )
    compression_result = await compression_manager.compress(
        CompressionInput(
            history=chat_request.history,
            latest_user_message=chat_request.message,
            retrieved_sources=retrieved_sources,
            execution_context=execution_context,
            options=build_compression_options(settings),
            model=generation_model,
            memory_context=memory_context or None,
        )
    )
    prompt_request = chat_request.model_copy(
        update={"history": compression_result.history}
    )
    retrieved_sources = compression_result.retrieved_sources
    ensure_attached_context_was_retrieved(
        chat_request,
        retrieved_sources,
        rag_warnings,
    )
    prompt = build_chat_prompt(
        prompt_request,
        max_chars=settings.chat_context_max_chars,
        retrieved_sources=retrieved_sources,
        memory_summary=compression_result.memory_summary,
        attachment_document_ids=current_attachment_document_ids(chat_request),
        broader_retrieval_used=context_selection.broader_retrieval_used,
        retrieval_mode=context_selection.mode,
    )
    log_document_context_debug(
        conversation_id=chat_request.conversationId,
        query=chat_request.message,
        selection=context_selection,
        retrieved_sources=retrieved_sources,
        document_context_included=bool(retrieved_sources),
    )
    logger.info(
        (
            "Prepared chat model=%s prompt_chars=%d history_messages=%d/%d "
            "retrieved_sources=%d context_mode=%s selected_document_ids=%s "
            "reranking_used=%s compression_used=%s"
        ),
        generation_model,
        len(prompt.text),
        prompt.included_history_messages,
        len(chat_request.history),
        prompt.retrieved_source_count,
        context_selection.mode,
        context_selection.selected_document_ids,
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
        compression_warnings=memory_warnings + compression_result.warnings,
        compression_stats=compression_result.stats.response_payload(),
        retrieved_sources=retrieved_sources,
        include_sources=include_sources,
        memory_store_warnings=[],
        limited_document_text_warning=limited_document_text_warning,
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
    memory_service: Annotated[
        ConversationMemoryService,
        Depends(get_conversation_memory_service),
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
    attached_documents = await resolve_attached_documents(chat_request, request)
    limited_document_text_warning = image_based_pdf_limited_text_warning(
        attached_documents
    )
    if attached_documents:
        logger.info(
            "Chat request received attachment_ids=%s",
            [document.get("documentId") for document in attached_documents],
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
    context_selection = DocumentContextSelection(
        mode="none",
        selected_document_ids=[],
    )
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

    context_selection = await retrieve_document_context(
        chat_request=chat_request,
        request=request,
        execution_context=execution_context,
        retrieval_pipeline=retrieval_pipeline,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    rag_result = context_selection.retrieval_result

    rag_warnings = list(rag_result.warnings if rag_result else [])
    rerank_warnings = list(rerank_plan.warnings)
    reranking_used = False
    reranker_model = rerank_plan.model
    retrieved_sources = rank_sources(
        rag_result.sources if rag_result else [],
        top_k=top_k,
    )
    ensure_attached_context_was_retrieved(
        chat_request,
        retrieved_sources,
        rag_warnings,
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

    memory_context, memory_warnings = await retrieve_conversation_memory_context(
        chat_request=chat_request,
        settings=settings,
        execution_context=execution_context,
        memory_service=memory_service,
    )
    compression_result = await compression_manager.compress(
        CompressionInput(
            history=chat_request.history,
            latest_user_message=chat_request.message,
            retrieved_sources=retrieved_sources,
            execution_context=execution_context,
            options=build_compression_options(settings),
            model=generation_model,
            memory_context=memory_context or None,
        )
    )
    prompt_request = chat_request.model_copy(
        update={"history": compression_result.history}
    )
    retrieved_sources = compression_result.retrieved_sources
    ensure_attached_context_was_retrieved(
        chat_request,
        retrieved_sources,
        rag_warnings,
    )
    prompt = build_chat_prompt(
        prompt_request,
        max_chars=settings.chat_context_max_chars,
        retrieved_sources=retrieved_sources,
        memory_summary=compression_result.memory_summary,
        attachment_document_ids=current_attachment_document_ids(chat_request),
        broader_retrieval_used=context_selection.broader_retrieval_used,
        retrieval_mode=context_selection.mode,
    )
    log_document_context_debug(
        conversation_id=chat_request.conversationId,
        query=chat_request.message,
        selection=context_selection,
        retrieved_sources=retrieved_sources,
        document_context_included=bool(retrieved_sources),
    )
    logger.info(
        (
            "Sending chat to Ollama model=%s prompt_chars=%d "
            "history_messages=%d/%d retrieved_sources=%d "
            "context_mode=%s selected_document_ids=%s "
            "reranking_used=%s compression_used=%s"
        ),
        generation_model,
        len(prompt.text),
        prompt.included_history_messages,
        len(chat_request.history),
        prompt.retrieved_source_count,
        context_selection.mode,
        context_selection.selected_document_ids,
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
    answer = strip_reasoning_text(answer)
    answer = repair_document_access_refusal(answer, retrieved_sources)
    answer = prepend_limited_document_warning(
        answer,
        limited_document_text_warning,
    )
    await store_durable_memory_from_chat(
        chat_request=chat_request,
        settings=settings,
        execution_context=execution_context,
        memory_service=memory_service,
    )

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
        compressionWarnings=memory_warnings + compression_result.warnings,
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
    memory_service: Annotated[
        ConversationMemoryService,
        Depends(get_conversation_memory_service),
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
        memory_service=memory_service,
    )

    async def event_stream() -> AsyncIterator[str]:
        yield _sse_event("progress", {"stage": "generating"})
        yield _sse_event("metadata", _chat_metadata_payload(prepared))

        answer_parts: list[str] = []
        reasoning_filter = ReasoningStreamFilter()
        try:
            async for chunk in llm_provider.stream_generate(
                prompt=prepared.prompt.text,
                history=[
                    item.model_dump() for item in prepared.prompt_request.history
                ],
                settings=prepared.generation_settings(),
            ):
                visible_chunk = reasoning_filter.feed(chunk)
                if visible_chunk:
                    answer_parts.append(visible_chunk)
                    yield _sse_event("token", {"text": visible_chunk})
        except Exception as exc:
            yield _sse_event("error", _stream_error_payload(exc))
            return

        final_visible_chunk = reasoning_filter.flush()
        if final_visible_chunk:
            answer_parts.append(final_visible_chunk)
            yield _sse_event("token", {"text": final_visible_chunk})

        final_answer = repair_document_access_refusal(
            "".join(answer_parts).strip(),
            prepared.retrieved_sources,
        )
        final_answer = prepend_limited_document_warning(
            final_answer,
            prepared.limited_document_text_warning,
        )
        settings: Settings = request.app.state.settings
        await store_durable_memory_from_chat(
            chat_request=chat_request,
            settings=settings,
            execution_context=prepared.execution_context,
            memory_service=memory_service,
        )
        yield _sse_event(
            "done",
            {
                **_chat_metadata_payload(prepared),
                "answer": final_answer,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

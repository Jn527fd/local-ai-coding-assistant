from typing import Annotated, Any
import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from app.ai.components import Chunk, ComponentUnavailableError
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.execution_context import AISettingsResolver
from app.ai.vectorstores import (
    VectorStoreBackend,
    VectorCollectionNotFoundError,
    VectorStoreError,
    VectorStoreValidationError,
)
from app.auth.api_key import require_api_key
from app.schemas.chat import ConversationSettings
from app.schemas.documents import (
    IndexDocumentRequest,
    ProcessDocumentRequest,
    SearchDocumentsRequest,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    DocumentValidationError,
)
from app.services.job_service import JobContext, JobService
from app.services.model_manager import ModelManager
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaServiceError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_api_key)],
)


def get_document_service(request: Request) -> DocumentService:
    """Return the configured local document service."""

    return request.app.state.document_service


def get_ai_settings_resolver(request: Request) -> AISettingsResolver:
    """Return the application AI settings resolver."""

    return request.app.state.ai_settings_resolver


def get_embedder_provider(request: Request) -> OllamaEmbedderProvider:
    """Return the configured embedding provider."""

    return request.app.state.embedder_provider


def get_vector_store(request: Request) -> VectorStoreBackend:
    """Return the local vector store."""

    return request.app.state.vector_store


def get_job_service(request: Request) -> JobService:
    """Return the local background job service."""

    return request.app.state.job_service


def parse_conversation_settings(
    raw_settings: str | None,
) -> ConversationSettings | None:
    if raw_settings is None or not raw_settings.strip():
        return None
    try:
        data: Any = json.loads(raw_settings)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversationSettings must be valid JSON.",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversationSettings must be a JSON object.",
        )
    return ConversationSettings.model_validate(data)


def raise_document_http_error(error: Exception) -> None:
    if isinstance(error, DocumentValidationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if isinstance(error, DocumentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, DocumentStorageError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    raise error


def require_embedder_model(execution_context: Any) -> str:
    embedder = execution_context.components["embedderModel"]
    if not execution_context.resolved_embedder_model or not embedder.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A valid available embedderModel is required before document "
                "chunks can be indexed or searched."
            ),
        )
    return execution_context.resolved_embedder_model


def raise_embedding_http_error(error: Exception) -> None:
    if isinstance(error, ComponentUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if isinstance(error, OllamaUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    if isinstance(error, OllamaTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(error),
        ) from error
    if isinstance(error, (OllamaResponseError, OllamaServiceError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    raise error


def raise_vector_http_error(error: Exception) -> None:
    if isinstance(error, VectorCollectionNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, VectorStoreValidationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if isinstance(error, VectorStoreError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    raise error


async def embed_texts_in_batches(
    embedder_provider: OllamaEmbedderProvider,
    texts: list[str],
    model: str,
    batch_size: int,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    safe_batch_size = max(1, batch_size)
    for start in range(0, len(texts), safe_batch_size):
        embeddings.extend(
            await embedder_provider.embed_texts(
                texts=texts[start : start + safe_batch_size],
                model=model,
            )
        )
    return embeddings


async def run_process_document(
    document_id: str,
    process_request: ProcessDocumentRequest,
    request: Request,
    document_service: DocumentService,
    settings_resolver: AISettingsResolver,
    job_context: JobContext | None = None,
) -> dict[str, Any]:
    if job_context is not None:
        await job_context.progress(10, "Resolving document settings.")
        job_context.check_cancelled()

    model_manager: ModelManager = request.app.state.model_manager
    execution_context = await settings_resolver.resolve(
        conversation_settings=process_request.conversationSettings,
        active_model=model_manager.active_model,
        conversation_id=process_request.conversationId,
    )
    if job_context is not None:
        await job_context.progress(30, "Extracting and chunking document.")
        job_context.check_cancelled()
    try:
        result = await run_in_threadpool(
            document_service.process,
            process_request.conversationId,
            document_id,
            execution_context,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)

    payload = {
        "document": result.metadata,
        "documentId": result.metadata["documentId"],
        "conversationId": result.metadata["conversationId"],
        "status": result.metadata["status"],
        "chunkCount": result.metadata["chunkCount"],
        "charLength": (
            result.extracted["charLength"]
            if result.extracted is not None
            else 0
        ),
        "warnings": result.metadata.get("extractionWarnings", []),
        "error": result.metadata.get("error"),
    }
    if job_context is not None:
        await job_context.progress(100, "Document processing completed.")
    return payload


async def run_index_document(
    document_id: str,
    index_request: IndexDocumentRequest,
    request: Request,
    document_service: DocumentService,
    settings_resolver: AISettingsResolver,
    embedder_provider: OllamaEmbedderProvider,
    vector_store: VectorStoreBackend,
    job_context: JobContext | None = None,
) -> dict[str, Any]:
    if job_context is not None:
        await job_context.progress(5, "Resolving indexing settings.")
        job_context.check_cancelled()

    model_manager: ModelManager = request.app.state.model_manager
    execution_context = await settings_resolver.resolve(
        conversation_settings=index_request.conversationSettings,
        active_model=model_manager.active_model,
        conversation_id=index_request.conversationId,
    )
    embedder_model = require_embedder_model(execution_context)

    try:
        document = await run_in_threadpool(
            document_service.get_document,
            index_request.conversationId,
            document_id,
        )
        chunks_payload = await run_in_threadpool(
            document_service.get_chunks,
            index_request.conversationId,
            document_id,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)

    if document.get("status") != "processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be processed before it can be indexed.",
        )

    raw_chunks = chunks_payload.get("chunks")
    if not isinstance(raw_chunks, list) or len(raw_chunks) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no processed chunks to index.",
        )

    chunks: list[Chunk] = []
    texts: list[str] = []
    for raw_chunk in raw_chunks:
        if not isinstance(raw_chunk, dict) or not isinstance(raw_chunk.get("text"), str):
            continue
        text = raw_chunk["text"]
        chunk_id = str(raw_chunk.get("chunkId") or f"{document_id}:{len(chunks)}")
        chunk_index = int(raw_chunk.get("index") or len(chunks))
        chunk_metadata = {
            **(
                raw_chunk.get("metadata")
                if isinstance(raw_chunk.get("metadata"), dict)
                else {}
            ),
            "documentId": document_id,
            "documentName": document.get("originalFilename") or "Document",
            "chunkId": chunk_id,
            "chunkIndex": chunk_index,
            "conversationId": index_request.conversationId,
            "charStart": raw_chunk.get("charStart"),
            "charEnd": raw_chunk.get("charEnd"),
            "tokenEstimate": raw_chunk.get("tokenEstimate"),
        }
        chunks.append(Chunk(id=chunk_id, text=text, metadata=chunk_metadata))
        texts.append(text)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document chunks artifact does not contain indexable text chunks.",
        )

    if job_context is not None:
        await job_context.progress(35, "Embedding document chunks.")
        job_context.check_cancelled()
    try:
        embeddings = await embed_texts_in_batches(
            embedder_provider=embedder_provider,
            texts=texts,
            model=embedder_model,
            batch_size=request.app.state.settings.embedding_batch_size,
        )
    except (
        ComponentUnavailableError,
        OllamaServiceError,
        OllamaUnavailableError,
        OllamaTimeoutError,
        OllamaResponseError,
    ) as exc:
        raise_embedding_http_error(exc)

    if job_context is not None:
        await job_context.progress(75, "Writing vector index.")
        job_context.check_cancelled()
    vector_database = execution_context.resolved_vector_database
    collection_id_factory = getattr(vector_store, "collection_id")
    collection_id = collection_id_factory(
        conversation_id=index_request.conversationId,
        embedder_model=embedder_model,
        vector_database=vector_database,
    )
    collection_ref = vector_store.collection_ref(
        index_request.conversationId,
        collection_id,
    )
    try:
        await vector_store.upsert(
            collection=collection_ref,
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                "embedderModel": embedder_model,
                "vectorDatabase": vector_database,
                "internalStore": vector_store.backend_id,
                "chunker": execution_context.resolved_chunker,
                "ragPipeline": execution_context.resolved_rag_pipeline,
                "documentIds": [document_id],
                "selectedSettings": execution_context.conversation_settings.model_dump(),
            },
        )
        collection = await vector_store.get_collection_metadata(collection_ref)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    payload = {
        "collection": collection,
        "collectionId": collection_id,
        "conversationId": index_request.conversationId,
        "documentId": document_id,
        "indexedChunks": len(chunks),
        "embedderModel": embedder_model,
        "vectorDatabase": vector_database,
        "internalStore": vector_store.backend_id,
        "warning": (
            f"Selected vector database '{vector_database}' is recorded, but "
            f"vectors were persisted in the '{vector_store.backend_id}' store."
            if vector_store.backend_id != vector_database
            else None
        ),
    }
    if job_context is not None:
        await job_context.progress(100, "Document indexing completed.")
    return payload


@router.post("/upload")
async def upload_document(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    conversationId: Annotated[str, Form(min_length=1, max_length=100)],
    file: Annotated[UploadFile, File()],
    conversationSettings: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """Stage one document under the requested local conversation."""

    settings = parse_conversation_settings(conversationSettings)
    content = await file.read(document_service.max_upload_bytes + 1)
    await file.close()
    if len(content) > document_service.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Document is larger than the configured upload limit.",
        )

    try:
        result = await run_in_threadpool(
            document_service.upload,
            conversationId,
            file.filename or "document",
            file.content_type,
            content,
            settings,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)

    return result.metadata


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    process_request: ProcessDocumentRequest,
    request: Request,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
) -> dict[str, Any]:
    """Extract text and create local chunks for a staged document."""

    return await run_process_document(
        document_id,
        process_request,
        request,
        document_service,
        settings_resolver,
    )


@router.post("/{document_id}/process/jobs", status_code=status.HTTP_202_ACCEPTED)
async def start_process_document_job(
    document_id: str,
    process_request: ProcessDocumentRequest,
    request: Request,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict[str, Any]:
    """Start local background processing for a staged document."""

    async def runner(job_context: JobContext) -> dict[str, Any]:
        return await run_process_document(
            document_id,
            process_request,
            request,
            document_service,
            settings_resolver,
            job_context,
        )

    job = job_service.create(
        "document.process",
        runner,
        target_type="document",
        target_id=document_id,
        payload={
            "conversationId": process_request.conversationId,
            "conversationSettings": (
                process_request.conversationSettings.model_dump()
                if process_request.conversationSettings is not None
                else None
            ),
        },
        message="Document processing queued.",
    )
    return {"job": job.model_dump(mode="json")}


@router.post("/{document_id}/index")
async def index_document(
    document_id: str,
    index_request: IndexDocumentRequest,
    request: Request,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    embedder_provider: Annotated[
        OllamaEmbedderProvider,
        Depends(get_embedder_provider),
    ],
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
) -> dict[str, Any]:
    """Embed and persist processed chunks for one conversation document."""

    return await run_index_document(
        document_id,
        index_request,
        request,
        document_service,
        settings_resolver,
        embedder_provider,
        vector_store,
    )


@router.post("/{document_id}/index/jobs", status_code=status.HTTP_202_ACCEPTED)
async def start_index_document_job(
    document_id: str,
    index_request: IndexDocumentRequest,
    request: Request,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    embedder_provider: Annotated[
        OllamaEmbedderProvider,
        Depends(get_embedder_provider),
    ],
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict[str, Any]:
    """Start local background indexing for a processed document."""

    async def runner(job_context: JobContext) -> dict[str, Any]:
        return await run_index_document(
            document_id,
            index_request,
            request,
            document_service,
            settings_resolver,
            embedder_provider,
            vector_store,
            job_context,
        )

    job = job_service.create(
        "document.index",
        runner,
        target_type="document",
        target_id=document_id,
        payload={
            "conversationId": index_request.conversationId,
            "conversationSettings": (
                index_request.conversationSettings.model_dump()
                if index_request.conversationSettings is not None
                else None
            ),
        },
        message="Document indexing queued.",
    )
    return {"job": job.model_dump(mode="json")}


@router.post("/search")
async def search_documents(
    search_request: SearchDocumentsRequest,
    request: Request,
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    embedder_provider: Annotated[
        OllamaEmbedderProvider,
        Depends(get_embedder_provider),
    ],
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
) -> dict[str, Any]:
    """Search indexed document chunks without injecting them into chat."""

    model_manager: ModelManager = request.app.state.model_manager
    execution_context = await settings_resolver.resolve(
        conversation_settings=search_request.conversationSettings,
        active_model=model_manager.active_model,
        conversation_id=search_request.conversationId,
    )
    embedder_model = require_embedder_model(execution_context)
    vector_database = execution_context.resolved_vector_database

    try:
        collections = await vector_store.list_collections(
            search_request.conversationId
        )
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    matching_collections = [
        collection
        for collection in collections
        if collection.get("embedderModel") == embedder_model
        and collection.get("vectorDatabase") == vector_database
        and collection.get("sourceType") != "repository"
    ]
    mismatched_collections = [
        collection
        for collection in collections
        if collection.get("embedderModel") != embedder_model
    ]
    if not matching_collections:
        if mismatched_collections:
            available_embedders = sorted(
                {
                    str(collection.get("embedderModel"))
                    for collection in mismatched_collections
                    if collection.get("embedderModel")
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Embedder mismatch: selected embedderModel "
                    f"'{embedder_model}' does not match indexed collection "
                    f"embedder(s): {', '.join(available_embedders)}."
                ),
            )
        return {
            "conversationId": search_request.conversationId,
            "query": search_request.query,
            "results": [],
            "warnings": ["No vector indexes exist for this conversation and settings."],
        }

    try:
        query_embedding = (
            await embedder_provider.embed_texts(
                texts=[search_request.query],
                model=embedder_model,
            )
        )[0]
    except (
        ComponentUnavailableError,
        OllamaServiceError,
        OllamaUnavailableError,
        OllamaTimeoutError,
        OllamaResponseError,
    ) as exc:
        raise_embedding_http_error(exc)

    document_ids = set(search_request.documentIds) if search_request.documentIds else None
    collection_refs = [
        vector_store.collection_ref(
            search_request.conversationId,
            str(collection["collectionId"]),
        )
        for collection in matching_collections
    ]
    try:
        search_results = await vector_store.search(
            collection_refs=collection_refs,
            query_embedding=query_embedding,
            top_k=search_request.topK,
            document_ids=document_ids,
        )
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    warnings: list[str] = []
    if mismatched_collections:
        warnings.append(
            "Skipped collections that were created with a different embedderModel."
        )

    return {
        "conversationId": search_request.conversationId,
        "query": search_request.query,
        "embedderModel": embedder_model,
        "vectorDatabase": vector_database,
        "topK": search_request.topK,
        "warnings": warnings,
        "results": [
            {
                "score": result.score,
                "collectionId": result.collection["collectionId"],
                "documentId": result.record["documentId"],
                "documentName": result.record.get("metadata", {}).get(
                    "documentName",
                    "Document",
                ),
                "chunkId": result.record["chunkId"],
                "chunkIndex": result.record["chunkIndex"],
                "text": result.record["text"],
                "metadata": result.record.get("metadata", {}),
            }
            for result in search_results
        ],
    }


@router.get("")
async def list_documents(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
) -> dict[str, Any]:
    """List documents scoped to one local conversation."""

    try:
        documents = await run_in_threadpool(
            document_service.list_documents,
            conversationId,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)

    return {"conversationId": conversationId, "documents": documents}


@router.get("/indexes")
async def list_document_indexes(
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
) -> dict[str, Any]:
    """List vector collections scoped to one conversation."""

    try:
        collections = await vector_store.list_collections(conversationId)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)
    return {
        "conversationId": conversationId,
        "indexes": [
            collection
            for collection in collections
            if collection.get("sourceType") != "repository"
        ],
    }


@router.delete("/indexes/{collection_id}")
async def delete_document_index(
    collection_id: str,
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
) -> dict[str, Any]:
    """Delete one vector collection owned by a conversation."""

    try:
        await vector_store.delete_collection(conversationId, collection_id)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)
    return {
        "deleted": True,
        "collectionId": collection_id,
        "conversationId": conversationId,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
) -> dict[str, Any]:
    """Return metadata and processing status for one conversation document."""

    try:
        document = await run_in_threadpool(
            document_service.get_document,
            conversationId,
            document_id,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)
    return document


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
) -> dict[str, Any]:
    """Return stored chunks for one conversation document."""

    try:
        return await run_in_threadpool(
            document_service.get_chunks,
            conversationId,
            document_id,
        )
    except (DocumentValidationError, DocumentNotFoundError, DocumentStorageError) as exc:
        raise_document_http_error(exc)

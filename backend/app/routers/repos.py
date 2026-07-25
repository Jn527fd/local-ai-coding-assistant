from hashlib import sha256
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.ai.components import Chunk
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.execution_context import AISettingsResolver
from app.ai.vectorstores import VectorStoreBackend, VectorStoreError
from app.auth.api_key import require_session_or_api_key
from app.config import Settings
from app.routers.documents import (
    embed_texts_in_batches,
    raise_embedding_http_error,
    raise_vector_http_error,
    require_embedder_model,
)
from app.rag.retriever import build_rag_prompt, retrieve_relevant_chunks
from app.schemas.repos import (
    AskRepositoryRequest,
    AskRepositoryResponse,
    IndexRepositoryVectorRequest,
    IndexRepositoryVectorResponse,
    IndexLocalRepositoryRequest,
    IndexLocalRepositoryResponse,
    SearchRepositoryVectorRequest,
)
from app.services.repo_service import (
    InvalidRepositoryPathError,
    RepositoryAccessError,
    RepositoryIndexNotFoundError,
    RepositoryIndexReadError,
    RepositoryIndexWriteError,
    RepositoryService,
)
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.services.model_manager import ModelManager

router = APIRouter(
    prefix="/repos",
    tags=["repositories"],
    dependencies=[Depends(require_session_or_api_key)],
)


def get_repository_service(request: Request) -> RepositoryService:
    """Build a repository service from the active application settings."""

    settings: Settings = request.app.state.settings
    return RepositoryService(
        index_directory=settings.index_directory,
        chunk_size=settings.repo_chunk_size,
        allowed_roots=settings.repository_allowed_root_paths,
        metadata_store=getattr(request.app.state, "metadata_store", None),
    )


def get_ollama_service(request: Request) -> OllamaService:
    """Build an Ollama client from the active application settings."""

    settings: Settings = request.app.state.settings
    return OllamaService(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
        num_predict=settings.ollama_num_predict,
        think=settings.ollama_think,
        keep_alive=settings.ollama_keep_alive,
    )


def get_ai_settings_resolver(request: Request) -> AISettingsResolver:
    return request.app.state.ai_settings_resolver


def get_embedder_provider(request: Request) -> OllamaEmbedderProvider:
    return request.app.state.embedder_provider


def get_vector_store(request: Request) -> VectorStoreBackend:
    return request.app.state.vector_store


def repository_collection_id(
    conversation_id: str,
    repo_name: str,
    embedder_model: str,
    vector_database: str,
) -> str:
    digest = sha256(
        f"repository\0{conversation_id}\0{repo_name}\0"
        f"{embedder_model}\0{vector_database}".encode("utf-8")
    ).hexdigest()[:16]
    return f"repo-{digest}"


def chunks_from_index(
    index_data: dict[str, Any],
    conversation_id: str,
) -> tuple[list[Chunk], list[str]]:
    repo_name = str(index_data.get("repo_name") or "repository")
    source_path = str(index_data.get("source_path") or "")
    chunks: list[Chunk] = []
    texts: list[str] = []
    for raw_chunk in index_data.get("chunks") or []:
        if not isinstance(raw_chunk, dict):
            continue
        text = raw_chunk.get("content")
        file_path = raw_chunk.get("file_path")
        start_line = raw_chunk.get("start_line")
        end_line = raw_chunk.get("end_line")
        chunk_id = raw_chunk.get("id")
        if (
            not isinstance(text, str)
            or not isinstance(file_path, str)
            or not isinstance(start_line, int)
            or not isinstance(end_line, int)
            or not isinstance(chunk_id, str)
        ):
            continue
        chunk_index = len(chunks)
        metadata = {
            "sourceType": "repository",
            "repositoryName": repo_name,
            "repositoryPath": source_path,
            "documentId": f"repository:{repo_name}",
            "documentName": repo_name,
            "filePath": file_path,
            "startLine": start_line,
            "endLine": end_line,
            "chunkId": chunk_id,
            "chunkIndex": chunk_index,
            "language": raw_chunk.get("language"),
            "chunkType": raw_chunk.get("chunk_type"),
            "symbolName": raw_chunk.get("symbol_name"),
            "symbolKind": raw_chunk.get("symbol_kind"),
            "parser": raw_chunk.get("parser"),
            "fallback": raw_chunk.get("fallback", False),
            "fallbackReason": raw_chunk.get("fallback_reason"),
            "conversationId": conversation_id,
        }
        chunks.append(Chunk(id=chunk_id, text=text, metadata=metadata))
        texts.append(text)
    return chunks, texts


@router.post("/index-local", response_model=IndexLocalRepositoryResponse)
async def index_local_repository(
    request: IndexLocalRepositoryRequest,
    repository_service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> IndexLocalRepositoryResponse:
    """Index supported files from a local repository into JSON."""

    try:
        result = await run_in_threadpool(
            repository_service.index_local,
            request.path,
        )
    except InvalidRepositoryPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RepositoryAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RepositoryIndexWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return IndexLocalRepositoryResponse(
        repo_name=result.repo_name,
        indexed_files=result.indexed_files,
        indexed_chunks=result.indexed_chunks,
        freshness={"fresh": True, "warnings": []},
        warnings=[],
    )


@router.post("/index-local/vector", response_model=IndexRepositoryVectorResponse)
async def index_local_repository_vectors(
    index_request: IndexRepositoryVectorRequest,
    request: Request,
    repository_service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
    settings_resolver: Annotated[
        AISettingsResolver,
        Depends(get_ai_settings_resolver),
    ],
    embedder_provider: Annotated[
        OllamaEmbedderProvider,
        Depends(get_embedder_provider),
    ],
    vector_store: Annotated[VectorStoreBackend, Depends(get_vector_store)],
) -> IndexRepositoryVectorResponse:
    """Opt into embedding repository chunks through the vector pipeline."""

    try:
        result = await run_in_threadpool(
            repository_service.index_local,
            index_request.path,
        )
        index_data = await run_in_threadpool(
            repository_service.load_index,
            result.repo_name,
        )
    except InvalidRepositoryPathError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RepositoryAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RepositoryIndexWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except RepositoryIndexReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    model_manager: ModelManager = request.app.state.model_manager
    execution_context = await settings_resolver.resolve(
        conversation_settings=index_request.conversationSettings,
        active_model=model_manager.active_model,
        conversation_id=index_request.conversationId,
    )
    embedder_model = require_embedder_model(execution_context)
    vector_database = execution_context.resolved_vector_database
    chunks, texts = chunks_from_index(index_data, index_request.conversationId)
    warnings: list[str] = []
    max_chunks = request.app.state.settings.document_max_chunks
    if len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]
        texts = texts[:max_chunks]
        warnings.append(
            f"Repository vector indexing was limited to {max_chunks} chunks."
        )
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository index has no chunks to embed.",
        )

    try:
        embeddings = await embed_texts_in_batches(
            embedder_provider=embedder_provider,
            texts=texts,
            model=embedder_model,
            batch_size=request.app.state.settings.embedding_batch_size,
        )
    except Exception as exc:
        raise_embedding_http_error(exc)

    collection_id = repository_collection_id(
        conversation_id=index_request.conversationId,
        repo_name=result.repo_name,
        embedder_model=embedder_model,
        vector_database=vector_database,
    )
    collection_ref = vector_store.collection_ref(
        index_request.conversationId,
        collection_id,
    )
    freshness = repository_service.freshness(index_data)
    try:
        await vector_store.upsert(
            collection=collection_ref,
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                "sourceType": "repository",
                "repositoryName": result.repo_name,
                "repositoryPath": index_data.get("source_path"),
                "repositoryFingerprint": index_data.get("fingerprint"),
                "repositoryIndexedAt": index_data.get("indexed_at"),
                "embedderModel": embedder_model,
                "vectorDatabase": vector_database,
                "internalStore": vector_store.backend_id,
                "documentIds": [f"repository:{result.repo_name}"],
                "selectedSettings": execution_context.conversation_settings.model_dump(),
            },
        )
        collection = await vector_store.get_collection_metadata(collection_ref)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    return IndexRepositoryVectorResponse(
        repo_name=result.repo_name,
        indexed_files=result.indexed_files,
        indexed_chunks=result.indexed_chunks,
        embedded_chunks=len(chunks),
        conversationId=index_request.conversationId,
        collectionId=collection_id,
        collection=dict(collection),
        embedderModel=embedder_model,
        vectorDatabase=vector_database,
        freshness=freshness,
        warnings=[*warnings, *freshness.get("warnings", [])],
    )


@router.post("/ask", response_model=AskRepositoryResponse)
async def ask_repository(
    request: AskRepositoryRequest,
    http_request: Request,
    repository_service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
    ollama_service: Annotated[
        OllamaService,
        Depends(get_ollama_service),
    ],
) -> AskRepositoryResponse:
    """Answer a question using relevant chunks from a repository index."""

    try:
        index_data = await run_in_threadpool(
            repository_service.load_index,
            request.repo_name,
        )
    except RepositoryIndexNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RepositoryIndexReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    settings: Settings = http_request.app.state.settings
    model_manager: ModelManager = http_request.app.state.model_manager
    if model_manager.is_switching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model switching is in progress. Try again when it completes.",
        )

    retrieved_chunks = retrieve_relevant_chunks(
        index_data=index_data,
        question=request.question,
        limit=settings.rag_top_k,
    )
    prompt = build_rag_prompt(
        repo_name=request.repo_name,
        question=request.question,
        chunks=retrieved_chunks,
    )

    try:
        answer = await ollama_service.generate(
            model=model_manager.active_model,
            prompt=prompt,
        )
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

    sources = list(dict.fromkeys(chunk.file_path for chunk in retrieved_chunks))
    freshness = repository_service.freshness(index_data)
    return AskRepositoryResponse(
        answer=answer,
        sources=sources,
        warnings=list(freshness.get("warnings", [])),
        freshness=freshness,
    )


@router.post("/search-vector")
async def search_repository_vectors(
    search_request: SearchRepositoryVectorRequest,
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
    """Search opt-in repository vector collections without using chat."""

    model_manager: ModelManager = request.app.state.model_manager
    execution_context = await settings_resolver.resolve(
        conversation_settings=search_request.conversationSettings,
        active_model=model_manager.active_model,
        conversation_id=search_request.conversationId,
    )
    embedder_model = require_embedder_model(execution_context)
    vector_database = execution_context.resolved_vector_database
    try:
        collections = await vector_store.list_collections(search_request.conversationId)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    matching_collections = [
        collection
        for collection in collections
        if collection.get("sourceType") == "repository"
        and collection.get("embedderModel") == embedder_model
        and collection.get("vectorDatabase") == vector_database
        and (
            search_request.repoName is None
            or collection.get("repositoryName") == search_request.repoName
        )
    ]
    if not matching_collections:
        return {
            "conversationId": search_request.conversationId,
            "query": search_request.query,
            "results": [],
            "warnings": ["No repository vector indexes match this conversation and settings."],
        }

    try:
        query_embedding = (
            await embedder_provider.embed_texts(
                texts=[search_request.query],
                model=embedder_model,
            )
        )[0]
    except Exception as exc:
        raise_embedding_http_error(exc)

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
        )
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

    warnings: list[str] = []
    repository_service = get_repository_service(request)
    for collection in matching_collections:
        index_name = collection.get("repositoryName")
        if not isinstance(index_name, str):
            continue
        try:
            index_data = await run_in_threadpool(
                repository_service.load_index,
                index_name,
            )
        except RepositoryIndexNotFoundError:
            warnings.append(
                f"Repository index '{index_name}' is missing; vector results may be stale."
            )
            continue
        except RepositoryIndexReadError:
            warnings.append(
                f"Repository index '{index_name}' could not be read; vector results may be stale."
            )
            continue
        warnings.extend(repository_service.freshness(index_data).get("warnings", []))

    return {
        "conversationId": search_request.conversationId,
        "query": search_request.query,
        "embedderModel": embedder_model,
        "vectorDatabase": vector_database,
        "topK": search_request.topK,
        "warnings": sorted(set(warnings)),
        "results": [
            {
                "score": result.score,
                "collectionId": result.collection["collectionId"],
                "repoName": result.collection.get("repositoryName"),
                "filePath": result.record.get("metadata", {}).get("filePath"),
                "startLine": result.record.get("metadata", {}).get("startLine"),
                "endLine": result.record.get("metadata", {}).get("endLine"),
                "language": result.record.get("metadata", {}).get("language"),
                "symbolName": result.record.get("metadata", {}).get("symbolName"),
                "symbolKind": result.record.get("metadata", {}).get("symbolKind"),
                "chunkId": result.record["chunkId"],
                "chunkIndex": result.record["chunkIndex"],
                "text": result.record["text"],
                "metadata": result.record.get("metadata", {}),
            }
            for result in search_results
        ],
    }

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.ai.vectorstores import (
    VectorCollectionNotFoundError,
    VectorStoreError,
    VectorStoreManager,
    VectorStoreValidationError,
)
from app.auth.api_key import require_api_key

router = APIRouter(
    prefix="/vectorstores",
    tags=["vectorstores"],
    dependencies=[Depends(require_api_key)],
)


class ImportCollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = Field(default="json", min_length=1, max_length=40)
    payload: dict[str, Any]


class MigrateCollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=100)
    collectionId: str = Field(min_length=1, max_length=120)
    sourceBackend: str = Field(default="json", min_length=1, max_length=40)
    targetBackend: str | None = Field(default=None, min_length=1, max_length=40)


def get_vector_store_manager(request: Request) -> VectorStoreManager:
    return request.app.state.vector_store_manager


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


@router.get("/health")
async def vector_store_health(
    manager: Annotated[VectorStoreManager, Depends(get_vector_store_manager)],
) -> dict[str, Any]:
    """Return vector backend availability and fallback diagnostics."""

    return manager.diagnostics()


@router.get("/collections/export")
async def export_collection(
    manager: Annotated[VectorStoreManager, Depends(get_vector_store_manager)],
    conversationId: Annotated[str, Query(min_length=1, max_length=100)],
    collectionId: Annotated[str, Query(min_length=1, max_length=120)],
    backend: Annotated[str, Query(min_length=1, max_length=40)] = "json",
) -> dict[str, Any]:
    """Export a vector collection in a portable local JSON format."""

    store = manager.store_by_id(backend)
    try:
        return await store.export_collection(conversationId, collectionId)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)


@router.post("/collections/import")
async def import_collection(
    request: ImportCollectionRequest,
    manager: Annotated[VectorStoreManager, Depends(get_vector_store_manager)],
) -> dict[str, Any]:
    """Import a portable vector collection payload into an available backend."""

    store = manager.store_by_id(request.backend)
    try:
        collection = await store.import_collection(request.payload)
    except VectorStoreError as exc:
        raise_vector_http_error(exc)
    return {
        "backend": store.backend_id,
        "fallbackUsed": store.backend_id != request.backend.strip().lower(),
        "collection": collection,
    }


@router.post("/collections/migrate")
async def migrate_collection(
    request: MigrateCollectionRequest,
    manager: Annotated[VectorStoreManager, Depends(get_vector_store_manager)],
) -> dict[str, Any]:
    """Copy one collection from a source backend to the requested target backend."""

    try:
        return await manager.migrate_collection(
            conversation_id=request.conversationId,
            collection_id=request.collectionId,
            source_backend=request.sourceBackend,
            target_backend=request.targetBackend,
        )
    except VectorStoreError as exc:
        raise_vector_http_error(exc)

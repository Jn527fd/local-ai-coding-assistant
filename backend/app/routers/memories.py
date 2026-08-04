from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.api_key import require_session_or_api_key
from app.schemas.memories import (
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryListResponse,
    MemorySearchRequest,
)
from app.services.conversation_memory import (
    ConversationMemoryError,
    ConversationMemoryService,
)

router = APIRouter(
    prefix="/memories",
    tags=["memories"],
    dependencies=[Depends(require_session_or_api_key)],
)


def _memory_service(request: Request) -> ConversationMemoryService:
    return request.app.state.conversation_memory_service


@router.post("", response_model=MemoryListResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_request: MemoryCreateRequest,
    service: Annotated[ConversationMemoryService, Depends(_memory_service)],
) -> MemoryListResponse:
    result = await service.store(
        workspace_id=memory_request.workspaceId,
        conversation_id=memory_request.conversationId,
        text=memory_request.text,
        memory_type=memory_request.type,
        importance=memory_request.importance,
        source_message_id=memory_request.sourceMessageId,
        source_role=memory_request.sourceRole,
        embedder_model=memory_request.embedderModel,
    )
    return MemoryListResponse(memories=result.memories, warnings=result.warnings)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    service: Annotated[ConversationMemoryService, Depends(_memory_service)],
    workspaceId: Annotated[str, Query(min_length=1, max_length=120)] = "default",
    conversationId: Annotated[str | None, Query(max_length=100)] = None,
) -> MemoryListResponse:
    result = service.list(
        workspace_id=workspaceId,
        conversation_id=conversationId,
        include_workspace_wide=True,
    )
    return MemoryListResponse(memories=result.memories, warnings=result.warnings)


@router.post("/search", response_model=MemoryListResponse)
async def search_memories(
    search_request: MemorySearchRequest,
    service: Annotated[ConversationMemoryService, Depends(_memory_service)],
) -> MemoryListResponse:
    result = await service.retrieve(
        workspace_id=search_request.workspaceId,
        conversation_id=search_request.conversationId,
        query=search_request.query,
        embedder_model=search_request.embedderModel,
        top_k=search_request.topK,
        memory_types=search_request.memoryTypes,
        min_importance=search_request.minImportance,
        include_workspace_wide=search_request.includeWorkspaceWide,
    )
    return MemoryListResponse(memories=result.memories, warnings=result.warnings)


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: str,
    request: Request,
    service: Annotated[ConversationMemoryService, Depends(_memory_service)],
    workspaceId: Annotated[str | None, Query(max_length=120)] = None,
) -> MemoryDeleteResponse:
    try:
        deleted = service.delete(memory_id=memory_id, workspace_id=workspaceId)
    except ConversationMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return MemoryDeleteResponse(deleted=deleted, memoryId=memory_id)


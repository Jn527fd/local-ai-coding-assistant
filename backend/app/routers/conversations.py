from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.auth.user_session import require_user_session
from app.schemas.conversations import (
    ConversationDeleteResponse,
    ConversationExportResponse,
    ConversationImportRequest,
    ConversationImportResponse,
    ConversationListResponse,
    ConversationRecord,
    ConversationResponse,
)
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationPersistenceService,
    ConversationStorageError,
)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


def _service(request: Request) -> ConversationPersistenceService:
    return request.app.state.conversation_service


def _storage_exception(exc: ConversationStorageError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationListResponse:
    service = _service(request)
    try:
        conversations = await run_in_threadpool(service.list, username)
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationListResponse(conversations=conversations)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    conversation: ConversationRecord,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationResponse:
    service = _service(request)
    try:
        saved = await run_in_threadpool(service.upsert, username, conversation)
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationResponse(conversation=saved)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationResponse:
    service = _service(request)
    try:
        conversation = await run_in_threadpool(
            service.get,
            username,
            conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationResponse(conversation=conversation)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation: ConversationRecord,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationResponse:
    service = _service(request)
    if conversation.id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation id in the path and body must match.",
        )
    try:
        saved = await run_in_threadpool(service.upsert, username, conversation)
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationResponse(conversation=saved)


@router.delete("/{conversation_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationDeleteResponse:
    service = _service(request)
    try:
        await run_in_threadpool(service.delete, username, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationDeleteResponse(
        deleted=True,
        conversationId=conversation_id,
    )


@router.post("/import", response_model=ConversationImportResponse)
async def import_conversations(
    import_request: ConversationImportRequest,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationImportResponse:
    service = _service(request)
    try:
        conversations = await run_in_threadpool(
            service.import_conversations,
            username,
            import_request.conversations,
            import_request.replace,
        )
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationImportResponse(
        imported=len(import_request.conversations),
        conversations=conversations,
    )


@router.get("/export/all", response_model=ConversationExportResponse)
async def export_conversations(
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> ConversationExportResponse:
    service = _service(request)
    try:
        payload = await run_in_threadpool(
            service.export_conversations,
            username,
        )
    except ConversationStorageError as exc:
        raise _storage_exception(exc) from exc
    return ConversationExportResponse.model_validate(payload)

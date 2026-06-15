from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.concurrency import run_in_threadpool

from app.auth.api_key import bearer_scheme
from app.auth.user_session import require_user_session
from app.config import Settings
from app.schemas.account import ApiKeyUpdateRequest, AccountStatusResponse
from app.services.local_settings_service import (
    LocalSettingsError,
    LocalSettingsService,
)

router = APIRouter(
    prefix="/account",
    tags=["account"],
)


def _account_status(
    username: str,
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
    local_settings: LocalSettingsService,
) -> AccountStatusResponse:
    fallback = settings.api_key.get_secret_value()
    active_key = local_settings.get_api_key(fallback=fallback)
    candidate = credentials.credentials if credentials else ""
    return AccountStatusResponse(
        username=username,
        api_key_configured=bool(active_key),
        api_key_active=local_settings.api_key_matches(
            candidate,
            fallback=fallback,
        ),
    )


@router.get("/status", response_model=AccountStatusResponse)
async def account_status(
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
) -> AccountStatusResponse:
    settings: Settings = request.app.state.settings
    local_settings: LocalSettingsService = (
        request.app.state.local_settings_service
    )
    try:
        return await run_in_threadpool(
            _account_status,
            username,
            credentials,
            settings,
            local_settings,
        )
    except LocalSettingsError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.put("/api-key", response_model=AccountStatusResponse)
async def update_api_key(
    update: ApiKeyUpdateRequest,
    request: Request,
    username: Annotated[str, Depends(require_user_session)],
) -> AccountStatusResponse:
    local_settings: LocalSettingsService = (
        request.app.state.local_settings_service
    )
    settings: Settings = request.app.state.settings

    try:
        await run_in_threadpool(local_settings.set_api_key, update.api_key)
        return await run_in_threadpool(
            _account_status,
            username,
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=update.api_key,
            ),
            settings,
            local_settings,
        )
    except LocalSettingsError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

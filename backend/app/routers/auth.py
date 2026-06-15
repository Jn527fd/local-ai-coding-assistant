from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.auth.credentials import (
    CredentialsConfigurationError,
    CredentialsService,
)
from app.auth.session import SessionService
from app.auth.user_session import require_user_session
from app.config import Settings
from app.schemas.auth import LoginRequest, SessionResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=SessionResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    response: Response,
) -> SessionResponse:
    """Authenticate a local user and set an HttpOnly session cookie."""

    credentials_service: CredentialsService = (
        request.app.state.credentials_service
    )
    session_service: SessionService = request.app.state.session_service
    settings: Settings = request.app.state.settings

    try:
        authenticated = await run_in_threadpool(
            credentials_service.authenticate,
            login_request.username,
            login_request.password,
        )
    except CredentialsConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = session_service.create(login_request.username)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessionResponse(username=login_request.username)


@router.get("/me", response_model=SessionResponse)
async def current_user(
    username: Annotated[str, Depends(require_user_session)],
) -> SessionResponse:
    return SessionResponse(username=username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    settings: Settings = request.app.state.settings
    session_service: SessionService = request.app.state.session_service
    session_service.revoke(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )

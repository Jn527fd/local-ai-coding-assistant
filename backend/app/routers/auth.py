from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.auth.credentials import (
    CredentialsConfigurationError,
    CredentialsService,
)
from app.auth.rate_limit import LoginRateLimiter
from app.auth.session import SessionService
from app.auth.user_session import _require_csrf_token, require_user_session
from app.config import Settings
from app.schemas.auth import LoginRequest, SessionResponse
from app.services.audit_log import AuditLogger

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
    login_rate_limiter: LoginRateLimiter = request.app.state.login_rate_limiter
    audit_logger: AuditLogger = request.app.state.audit_logger
    settings: Settings = request.app.state.settings
    client_host = request.client.host if request.client else ""
    rate_limit_key = f"{client_host}:{login_request.username}"

    if login_rate_limiter.is_limited(rate_limit_key):
        audit_logger.auth_event(
            "login_limited",
            username=login_request.username,
            client_host=client_host,
            success=False,
            reason="rate_limited",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

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
        limited = login_rate_limiter.record_failure(rate_limit_key)
        audit_logger.auth_event(
            "login_failed",
            username=login_request.username,
            client_host=client_host,
            success=False,
            reason="invalid_credentials",
        )
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    login_rate_limiter.record_success(rate_limit_key)
    token = session_service.create(login_request.username)
    csrf_token = session_service.create_csrf_token()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    audit_logger.auth_event(
        "login_succeeded",
        username=login_request.username,
        client_host=client_host,
        success=True,
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
    audit_logger: AuditLogger = request.app.state.audit_logger
    _require_csrf_token(request, settings)
    username = session_service.username_for(
        request.cookies.get(settings.session_cookie_name)
    )
    session_service.revoke(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
    )
    audit_logger.auth_event(
        "logout",
        username=username or "",
        client_host=request.client.host if request.client else "",
        success=True,
    )

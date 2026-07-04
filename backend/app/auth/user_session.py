import hmac

from fastapi import HTTPException, Request, status

from app.auth.session import SessionService
from app.config import Settings


def require_user_session(
    request: Request,
) -> str:
    """Require a valid HttpOnly browser login session."""

    settings: Settings = request.app.state.settings
    session_service: SessionService = request.app.state.session_service

    token = request.cookies.get(settings.session_cookie_name)
    username = session_service.username_for(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required.",
        )

    _require_csrf_token(request, settings)
    return username


def _require_csrf_token(request: Request, settings: Settings) -> None:
    if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return

    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    csrf_header = request.headers.get(settings.csrf_header_name)
    if csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="CSRF token missing or invalid.",
    )

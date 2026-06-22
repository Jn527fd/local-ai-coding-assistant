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

    return username

from hmac import compare_digest
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="API key configured through the backend API_KEY environment variable.",
)


def require_api_key(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
) -> str:
    """Validate the bearer API key for a protected endpoint."""

    settings: Settings = request.app.state.settings
    expected_api_key = settings.api_key.get_secret_value()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured on the server.",
        )

    if credentials is None or not compare_digest(
        credentials.credentials.encode("utf-8"),
        expected_api_key.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials

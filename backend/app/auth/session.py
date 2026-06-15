from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from threading import Lock


@dataclass(frozen=True)
class UserSession:
    """An authenticated local browser session."""

    username: str
    expires_at: datetime


class SessionService:
    """Store short-lived browser sessions in backend memory."""

    def __init__(self, ttl_hours: int) -> None:
        self.ttl = timedelta(hours=ttl_hours)
        self._sessions: dict[str, UserSession] = {}
        self._lock = Lock()

    def create(self, username: str) -> str:
        """Create a cryptographically random session token."""

        token = token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + self.ttl
        with self._lock:
            self._remove_expired_locked()
            self._sessions[token] = UserSession(
                username=username,
                expires_at=expires_at,
            )
        return token

    def username_for(self, token: str | None) -> str | None:
        """Return the session username when the token is valid."""

        if not token:
            return None

        with self._lock:
            self._remove_expired_locked()
            session = self._sessions.get(token)
            return session.username if session else None

    def revoke(self, token: str | None) -> None:
        """Remove a session token if it exists."""

        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def _remove_expired_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token
            for token, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for token in expired_tokens:
            self._sessions.pop(token, None)

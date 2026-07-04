from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from base64 import urlsafe_b64decode, urlsafe_b64encode
import hmac
from secrets import token_urlsafe
from hashlib import sha256
from threading import Lock


@dataclass(frozen=True)
class UserSession:
    """An authenticated local browser session."""

    username: str
    expires_at: datetime


class SessionService:
    """Store short-lived browser sessions, optionally signed for restarts."""

    def __init__(self, ttl_hours: int, signing_key: str = "") -> None:
        self.ttl = timedelta(hours=ttl_hours)
        self.signing_key = signing_key
        self._sessions: dict[str, UserSession] = {}
        self._revoked_tokens: set[str] = set()
        self._lock = Lock()

    def create(self, username: str) -> str:
        """Create a cryptographically random session token."""

        expires_at = datetime.now(timezone.utc) + self.ttl
        if self.signing_key:
            token = self._sign_token(username, expires_at)
        else:
            token = token_urlsafe(32)
        with self._lock:
            self._remove_expired_locked()
            self._sessions[token] = UserSession(
                username=username,
                expires_at=expires_at,
            )
        return token

    def create_csrf_token(self) -> str:
        """Create a browser-readable CSRF token for double-submit checks."""

        return token_urlsafe(32)

    def username_for(self, token: str | None) -> str | None:
        """Return the session username when the token is valid."""

        if not token:
            return None

        with self._lock:
            self._remove_expired_locked()
            if token in self._revoked_tokens:
                return None
            session = self._sessions.get(token)
            if session:
                return session.username

        if not self.signing_key:
            return None
        return self._verify_signed_token(token)

    def revoke(self, token: str | None) -> None:
        """Remove a session token if it exists."""

        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)
            if self.signing_key:
                self._revoked_tokens.add(token)

    def _remove_expired_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token
            for token, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for token in expired_tokens:
            self._sessions.pop(token, None)

    def _sign_token(self, username: str, expires_at: datetime) -> str:
        expires_ts = str(int(expires_at.timestamp()))
        nonce = token_urlsafe(16)
        encoded_username = urlsafe_b64encode(username.encode("utf-8")).decode(
            "ascii"
        )
        payload = f"v1.{encoded_username}.{expires_ts}.{nonce}"
        signature = hmac.new(
            self.signing_key.encode("utf-8"),
            payload.encode("utf-8"),
            sha256,
        ).hexdigest()
        return f"{payload}.{signature}"

    def _verify_signed_token(self, token: str) -> str | None:
        parts = token.split(".")
        if len(parts) != 5 or parts[0] != "v1":
            return None
        payload = ".".join(parts[:4])
        expected_signature = hmac.new(
            self.signing_key.encode("utf-8"),
            payload.encode("utf-8"),
            sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, parts[4]):
            return None
        try:
            expires_at = datetime.fromtimestamp(int(parts[2]), tz=timezone.utc)
        except ValueError:
            return None
        if expires_at <= datetime.now(timezone.utc):
            return None
        try:
            return urlsafe_b64decode(parts[1].encode("ascii")).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return None

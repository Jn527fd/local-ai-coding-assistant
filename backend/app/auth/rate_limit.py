from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


@dataclass
class LoginAttemptState:
    attempts: int
    first_attempt_at: datetime
    locked_until: datetime | None = None


class LoginRateLimiter:
    """Small in-memory limiter for local login attempts."""

    def __init__(
        self,
        attempts: int,
        window_seconds: int,
        lockout_seconds: int,
    ) -> None:
        self.attempts = attempts
        self.window = timedelta(seconds=window_seconds)
        self.lockout = timedelta(seconds=lockout_seconds)
        self._states: dict[str, LoginAttemptState] = {}
        self._lock = Lock()

    def is_limited(self, key: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            state = self._states.get(key)
            if not state:
                return False
            if state.locked_until and state.locked_until > now:
                return True
            if state.first_attempt_at + self.window <= now:
                self._states.pop(key, None)
            return False

    def record_failure(self, key: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            state = self._states.get(key)
            if not state or state.first_attempt_at + self.window <= now:
                self._states[key] = LoginAttemptState(
                    attempts=1,
                    first_attempt_at=now,
                )
                return False

            state.attempts += 1
            if state.attempts >= self.attempts:
                state.locked_until = now + self.lockout
                return True
            return False

    def record_success(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)

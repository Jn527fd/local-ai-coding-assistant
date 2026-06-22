import base64
from hashlib import pbkdf2_hmac
from hmac import compare_digest
import json
import os
from pathlib import Path
from secrets import token_bytes
from typing import Any

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000
MIN_PASSWORD_LENGTH = 8


class CredentialsError(Exception):
    """Base error raised while loading or validating local credentials."""


class CredentialsConfigurationError(CredentialsError):
    """Raised when the local credentials file is missing or invalid."""


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Return a salted PBKDF2 password hash suitable for the credentials file."""

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    salt = token_bytes(16)
    digest = pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return (
        f"pbkdf2_{PBKDF2_ALGORITHM}${iterations}$"
        f"{encoded_salt}${encoded_digest}"
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Check a password against a stored PBKDF2 hash."""

    try:
        scheme, iterations_text, encoded_salt, encoded_digest = (
            encoded_hash.split("$", maxsplit=3)
        )
        if scheme != f"pbkdf2_{PBKDF2_ALGORITHM}":
            return False

        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False

        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(
            encoded_digest.encode("ascii")
        )
    except (ValueError, TypeError):
        return False

    candidate_digest = pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return compare_digest(candidate_digest, expected_digest)


class CredentialsService:
    """Authenticate users against an ignored, locally editable JSON file."""

    def __init__(self, credentials_file: Path) -> None:
        self.credentials_file = credentials_file

    def authenticate(self, username: str, password: str) -> bool:
        """Return whether a username and password match a configured user."""

        users = self._load_users()
        for user in users:
            stored_username = user.get("username")
            password_hash = user.get("password_hash")
            if not isinstance(stored_username, str) or not isinstance(
                password_hash, str
            ):
                continue

            if compare_digest(stored_username, username):
                return verify_password(password, password_hash)

        return False

    def _load_users(self) -> list[dict[str, Any]]:
        if not self.credentials_file.is_file():
            raise CredentialsConfigurationError(
                "Local credentials are not configured. Create "
                f"{self.credentials_file} before signing in."
            )

        try:
            data: Any = json.loads(
                self.credentials_file.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CredentialsConfigurationError(
                f"Unable to read credentials file: {self.credentials_file}"
            ) from exc

        users = data.get("users") if isinstance(data, dict) else None
        if not isinstance(users, list):
            raise CredentialsConfigurationError(
                "Credentials file must contain a 'users' array."
            )

        return [user for user in users if isinstance(user, dict)]


def write_credentials_file(path: Path, users: list[dict[str, str]]) -> None:
    """Atomically write a credentials file with private permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps({"users": users}, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)

    if os.name == "posix":
        path.chmod(0o600)

from __future__ import annotations

import argparse
from getpass import getpass
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_CREDENTIALS_FILE = (
    PROJECT_ROOT / "data" / "config" / "credentials.json"
)
sys.path.insert(0, str(BACKEND_ROOT))

from app.auth.credentials import hash_password, write_credentials_file  # noqa: E402

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def load_users(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read {path}: {exc}") from exc

    users = data.get("users") if isinstance(data, dict) else None
    if not isinstance(users, list):
        raise SystemExit("Credentials file must contain a 'users' array.")

    return [
        user
        for user in users
        if isinstance(user, dict)
        and isinstance(user.get("username"), str)
        and isinstance(user.get("password_hash"), str)
    ]


def set_user(path: Path, username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise SystemExit(
            "Username must use 1-100 letters, numbers, dots, dashes, or "
            "underscores."
        )

    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    users = load_users(path)
    updated_user = {
        "username": username,
        "password_hash": password_hash,
    }
    for index, user in enumerate(users):
        if user["username"] == username:
            users[index] = updated_user
            break
    else:
        users.append(updated_user)

    users.sort(key=lambda user: user["username"].lower())
    write_credentials_file(path, users)
    print(f"Saved local credentials for '{username}' in {path}.")


def remove_user(path: Path, username: str) -> None:
    users = load_users(path)
    remaining = [user for user in users if user["username"] != username]
    if len(remaining) == len(users):
        raise SystemExit(f"User '{username}' was not found.")
    write_credentials_file(path, remaining)
    print(f"Removed '{username}' from {path}.")


def list_users(path: Path) -> None:
    users = load_users(path)
    if not users:
        print("No local users configured.")
        return
    for user in users:
        print(user["username"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage hashed local login credentials.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_CREDENTIALS_FILE,
        help="Credentials JSON path.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Add or update a user.")
    set_parser.add_argument("username")

    remove_parser = subparsers.add_parser("remove", help="Remove a user.")
    remove_parser.add_argument("username")

    subparsers.add_parser("list", help="List configured usernames.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.file.expanduser().resolve()
    if args.command == "set":
        set_user(path, args.username)
    elif args.command == "remove":
        remove_user(path, args.username)
    else:
        list_users(path)


if __name__ == "__main__":
    main()

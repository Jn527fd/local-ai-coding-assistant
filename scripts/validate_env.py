from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate_environment(root: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    root_env = root / ".env"
    backend_env = root / "backend" / ".env"
    credentials_file = root / "data" / "config" / "credentials.json"

    if not root_env.exists():
        warnings.append("Root .env is missing; copy .env.example before production deploys.")
    if not backend_env.exists():
        errors.append("backend/.env is missing; copy backend/.env.example and set local values.")
    if not credentials_file.exists():
        errors.append("data/config/credentials.json is missing; create local login credentials.")

    root_values = parse_env_file(root_env)
    backend_values = parse_env_file(backend_env)

    api_key = backend_values.get("API_KEY", "")
    if not api_key:
        warnings.append("API_KEY is empty; save a Bearer key in Settings before using AI/data APIs.")
    elif len(api_key) < 24:
        warnings.append("API_KEY is short; use a longer private key for normal deployments.")

    if not backend_values.get("SESSION_SIGNING_KEY"):
        warnings.append("SESSION_SIGNING_KEY is empty; browser sessions will end on backend restart.")

    if backend_values.get("APP_DEBUG", "false").lower() == "true":
        errors.append("APP_DEBUG=true is unsafe for production.")

    if backend_values.get("SESSION_COOKIE_SECURE", "false").lower() == "false":
        warnings.append("SESSION_COOKIE_SECURE=false is only safe for local HTTP or trusted LAN testing.")

    ollama_url = backend_values.get("OLLAMA_BASE_URL", root_values.get("OLLAMA_BASE_URL", ""))
    if "0.0.0.0" in ollama_url:
        errors.append("OLLAMA_BASE_URL must not point at 0.0.0.0.")

    frontend_bind = root_values.get("FRONTEND_BIND_ADDRESS", "127.0.0.1")
    if frontend_bind in {"0.0.0.0", "::"}:
        warnings.append("FRONTEND_BIND_ADDRESS exposes the UI on all interfaces; prefer a reverse proxy.")

    repos_root = root_values.get("LOCAL_REPOS_ROOT", ".")
    if repos_root == ".":
        warnings.append("LOCAL_REPOS_ROOT=. mounts the project directory; use a dedicated read-only repo root.")

    return ValidationResult(errors=errors, warnings=warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local deployment environment files.")
    parser.add_argument("--root", default=".", help="Repository root to validate.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args()

    result = validate_environment(Path(args.root).resolve())
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.errors or (args.strict and result.warnings):
        return 1
    print("Environment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

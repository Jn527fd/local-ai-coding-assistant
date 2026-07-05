from pathlib import Path
import zipfile

from scripts.upgrade import create_backup
from scripts.validate_env import validate_environment


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validate_environment_reports_missing_required_files(tmp_path: Path) -> None:
    result = validate_environment(tmp_path)

    assert not result.ok
    assert any("backend/.env is missing" in error for error in result.errors)
    assert any("credentials.json is missing" in error for error in result.errors)


def test_validate_environment_accepts_safe_minimum(tmp_path: Path) -> None:
    write_text(
        tmp_path / ".env",
        "FRONTEND_BIND_ADDRESS=127.0.0.1\nLOCAL_REPOS_ROOT=/srv/repos\n",
    )
    write_text(
        tmp_path / "backend" / ".env",
        "\n".join(
            [
                "API_KEY=abcdefghijklmnopqrstuvwxyz123456",
                "SESSION_SIGNING_KEY=stable-local-signing-key",
                "SESSION_COOKIE_SECURE=true",
                "APP_DEBUG=false",
                "OLLAMA_BASE_URL=http://127.0.0.1:11434",
            ]
        ),
    )
    write_text(tmp_path / "data" / "config" / "credentials.json", "[]")

    result = validate_environment(tmp_path)

    assert result.ok
    assert result.errors == []


def test_validate_environment_rejects_unsafe_debug_and_ollama_bind(
    tmp_path: Path,
) -> None:
    write_text(tmp_path / ".env", "FRONTEND_BIND_ADDRESS=0.0.0.0\n")
    write_text(
        tmp_path / "backend" / ".env",
        "APP_DEBUG=true\nOLLAMA_BASE_URL=http://0.0.0.0:11434\n",
    )
    write_text(tmp_path / "data" / "config" / "credentials.json", "[]")

    result = validate_environment(tmp_path)

    assert any("APP_DEBUG=true" in error for error in result.errors)
    assert any("0.0.0.0" in error for error in result.errors)
    assert any("FRONTEND_BIND_ADDRESS" in warning for warning in result.warnings)


def test_create_backup_archives_data_before_upgrade(tmp_path: Path) -> None:
    write_text(tmp_path / "data" / "config" / "app-settings.json", "{}")

    archive = create_backup(tmp_path)

    assert archive.exists()
    assert archive.suffix == ".zip"
    with zipfile.ZipFile(archive) as backup:
        assert "config/app-settings.json" in backup.namelist()

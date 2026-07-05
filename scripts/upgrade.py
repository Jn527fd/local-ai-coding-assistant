from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from validate_env import validate_environment
except ModuleNotFoundError:
    from scripts.validate_env import validate_environment


def create_backup(root: Path, backup_dir: Path | None = None) -> Path:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target_dir = backup_dir or root / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = target_dir / f"pre-upgrade-data-{timestamp}"
    archive = shutil.make_archive(str(base_name), "zip", data_dir)
    return Path(archive)


def run_compose_upgrade(root: Path, compose_file: str) -> None:
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "pull"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "--build", "--detach"],
        cwd=root,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up local data before replacing Compose services.",
    )
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument(
        "--compose-file",
        default="docker-compose.prod.yml",
        help="Compose file to use for the upgrade.",
    )
    parser.add_argument("--backup-dir", default="", help="Optional backup directory.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run Docker Compose after backup. Without this, only validate and back up.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    validation = validate_environment(root)
    for warning in validation.warnings:
        print(f"WARNING: {warning}")
    for error in validation.errors:
        print(f"ERROR: {error}")
    if validation.errors:
        print("Upgrade stopped before backup because validation failed.")
        return 1

    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else None
    archive = create_backup(root, backup_dir)
    print(f"Created data backup: {archive}")

    if not args.apply:
        print("Dry run complete. Re-run with --apply to replace Compose services.")
        return 0

    try:
        run_compose_upgrade(root, args.compose_file)
    except subprocess.CalledProcessError as exc:
        print(f"Docker Compose upgrade failed after backup: {exc}", file=sys.stderr)
        return exc.returncode or 1

    print("Compose services upgraded after successful backup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

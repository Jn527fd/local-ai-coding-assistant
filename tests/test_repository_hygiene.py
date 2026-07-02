import shutil
import subprocess
from pathlib import Path

import pytest


def test_no_tracked_files_match_gitignore() -> None:
    """Ignored local artifacts should not be committed to the repository."""

    repo_root = Path(__file__).resolve().parents[1]
    if not (repo_root / ".git").exists():
        pytest.skip("Repository metadata is not available in this test context.")
    if shutil.which("git") is None:
        pytest.skip("git is not available in this test context.")

    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_ignored_files = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    assert tracked_ignored_files == []

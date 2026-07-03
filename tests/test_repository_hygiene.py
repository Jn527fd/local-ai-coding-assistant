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


def test_release_readiness_documents_exist_and_cover_required_topics() -> None:
    """Phase 15 release docs should remain present and actionable."""

    repo_root = Path(__file__).resolve().parents[1]
    required_docs = {
        "SECURITY.md": [
            "Trust Model",
            "Sensitive Data",
            "Before Broader Deployment",
        ],
        "CHANGELOG.md": [
            "[0.1.0]",
            "Known Limitations",
        ],
        "docs/deployment-hardening.md": [
            "HTTPS Reverse Proxy",
            "Cookie and API-Key Settings",
            "Operational Smoke Check",
        ],
        "docs/backup-restore.md": [
            "Data to Back Up",
            "Restore",
            "Browser Chat History",
        ],
        "docs/dependency-security.md": [
            "Dependency Sources",
            "Useful Audit Commands",
            "Secret and Artifact Hygiene",
        ],
        "docs/release-checklist.md": [
            "Required Tests",
            "Docker Verification",
            "Manual Smoke",
        ],
        "roadmap_v2.md": [
            "Roadmap v2",
            "Phase 1: Release Candidate Stabilization",
            "Phase 15: Public Release Candidate QA",
        ],
    }

    for relative_path, required_phrases in required_docs.items():
        document = repo_root / relative_path
        assert document.exists(), f"{relative_path} is missing"
        content = document.read_text(encoding="utf-8")
        for phrase in required_phrases:
            assert phrase in content, f"{relative_path} missing {phrase!r}"

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from app.schemas.chat import ChatImageAttachment
from app.schemas.vision import VisionEvidenceArtifact
from app.services.vision_artifacts import VisionArtifactService


class FakeVisionOllamaService:
    def __init__(self, response: str | None = None, fail: bool = False) -> None:
        self.response = response or json.dumps(
            {
                "visibleText": ["ModuleNotFoundError: No module named 'qdrant_client'"],
                "errors": ["ModuleNotFoundError: No module named 'qdrant_client'"],
                "filePaths": ["backend/app/ai/vectorstores/qdrant.py"],
                "code": ["from qdrant_client import QdrantClient"],
                "uiElements": ["terminal"],
                "observations": ["pytest output is visible"],
                "uncertainties": [],
            }
        )
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ) -> str:
        self.calls.append({"model": model, "prompt": prompt, "images": images or []})
        if self.fail:
            raise RuntimeError("vision offline")
        return self.response


def image_attachment(image_id: str = "image-a") -> ChatImageAttachment:
    return ChatImageAttachment(
        id=image_id,
        name="error.png",
        mimeType="image/png",
        data=base64.b64encode(b"fake image").decode("ascii"),
    )


def artifact(
    artifact_id: str,
    *,
    workspace_id: str = "default",
    conversation_id: str = "conversation-a",
    message_id: str = "message-a",
    image_id: str = "image-a",
    created_at: datetime | None = None,
    visible_text: list[str] | None = None,
    errors: list[str] | None = None,
    file_paths: list[str] | None = None,
    code: list[str] | None = None,
    observations: list[str] | None = None,
) -> VisionEvidenceArtifact:
    return VisionEvidenceArtifact(
        id=artifact_id,
        workspaceId=workspace_id,
        conversationId=conversation_id,
        messageId=message_id,
        imageId=image_id,
        imageName=f"{image_id}.png",
        mimeType="image/png",
        visionModel="llava:latest",
        createdAt=created_at or datetime.now(timezone.utc),
        status="succeeded",
        visibleText=visible_text or [],
        errors=errors or [],
        filePaths=file_paths or [],
        code=code or [],
        uiElements=[],
        observations=observations or [],
        uncertainties=[],
    )


def write_artifacts(
    service: VisionArtifactService,
    workspace_id: str,
    conversation_id: str,
    artifacts: list[VisionEvidenceArtifact],
) -> None:
    path = service.storage_directory / workspace_id / f"{conversation_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspaceId": workspace_id,
                "conversationId": conversation_id,
                "artifacts": [
                    item.model_dump(mode="json")
                    for item in artifacts
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_vision_artifact_persists_structured_exact_evidence(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())

    result = await service.analyze_images(
        conversation_id="conversation-a",
        message_id="message-a",
        images=[image_attachment()],
        vision_model="llava:latest",
    )
    second_service = VisionArtifactService(
        tmp_path / "vision",
        FakeVisionOllamaService(),
    )
    retrieved = second_service.retrieve_relevant(
        "conversation-a",
        "qdrant_client error",
    )

    assert result.warnings == []
    assert len(result.artifacts) == 1
    artifact = retrieved.artifacts[0]
    assert artifact.workspaceId == "default"
    assert artifact.conversationId == "conversation-a"
    assert artifact.messageId == "message-a"
    assert artifact.imageId == "image-a"
    assert artifact.visibleText == ["ModuleNotFoundError: No module named 'qdrant_client'"]
    assert artifact.filePaths == ["backend/app/ai/vectorstores/qdrant.py"]
    assert artifact.code == ["from qdrant_client import QdrantClient"]


@pytest.mark.asyncio
async def test_vision_artifact_failure_persists_fallback_artifact(tmp_path: Path):
    service = VisionArtifactService(
        tmp_path / "vision",
        FakeVisionOllamaService(fail=True),
    )

    result = await service.analyze_images(
        conversation_id="conversation-a",
        message_id="message-a",
        images=[image_attachment()],
        vision_model="llava:latest",
    )

    assert "Image evidence extraction failed" in result.warnings[0]
    assert result.artifacts[0].status == "failed"
    assert result.artifacts[0].uncertainties


def test_vision_artifact_retrieval_is_conversation_isolated(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())

    write_artifacts(
        service,
        "default",
        "conversation-b",
        [artifact("artifact-b", conversation_id="conversation-b", visible_text=["private other conversation"])],
    )

    assert service.retrieve_relevant("conversation-a", "private").artifacts == []


def test_vision_artifact_retrieval_is_workspace_isolated(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    write_artifacts(
        service,
        "workspace-b",
        "conversation-a",
        [
            artifact(
                "artifact-b",
                workspace_id="workspace-b",
                visible_text=["workspace secret qdrant_client traceback"],
            )
        ],
    )

    assert service.retrieve_relevant(
        "conversation-a",
        "qdrant_client traceback",
        workspace_id="workspace-a",
    ).artifacts == []


def test_vision_retrieval_prioritizes_exact_identifiers_then_recency(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    older = datetime.now(timezone.utc) - timedelta(days=1)
    newer = datetime.now(timezone.utc)
    write_artifacts(
        service,
        "default",
        "conversation-a",
        [
            artifact(
                "recent-semantic",
                created_at=newer,
                visible_text=["A recent screenshot shows a Python exception."],
            ),
            artifact(
                "older-exact",
                created_at=older,
                file_paths=["backend/app/ai/vectorstores/qdrant.py"],
                errors=["Import failed."],
            ),
            artifact(
                "newer-exact",
                created_at=newer,
                file_paths=["backend/app/ai/vectorstores/qdrant.py"],
                errors=["Second exact match."],
            ),
        ],
    )

    result = service.retrieve_relevant(
        "conversation-a",
        "What exception is shown and where is backend/app/ai/vectorstores/qdrant.py mentioned?",
        limit=3,
    )

    assert [item.id for item in result.artifacts] == [
        "newer-exact",
        "older-exact",
        "recent-semantic",
    ]


def test_vision_retrieval_always_includes_current_artifacts_first(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    current = artifact("current", visible_text=["unrelated color palette"])
    prior = artifact("prior", errors=["ModuleNotFoundError: qdrant_client"])
    write_artifacts(service, "default", "conversation-a", [prior])

    result = service.retrieve_relevant(
        "conversation-a",
        "qdrant_client error",
        current_artifacts=[current],
        limit=2,
    )

    assert [item.id for item in result.artifacts] == ["current", "prior"]


def test_vision_retrieval_rejects_irrelevant_prior_artifacts(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    write_artifacts(
        service,
        "default",
        "conversation-a",
        [
            artifact(
                "irrelevant",
                visible_text=["A calendar appointment for lunch is visible."],
            )
        ],
    )

    assert service.retrieve_relevant(
        "conversation-a",
        "qdrant_client traceback",
    ).artifacts == []


def test_vision_retrieval_handles_semantic_paraphrase_without_vectors(
    tmp_path: Path,
):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    write_artifacts(
        service,
        "default",
        "conversation-a",
        [
            artifact(
                "semantic",
                errors=["Traceback shows an exception in the screenshot."],
            )
        ],
    )

    result = service.retrieve_relevant("conversation-a", "What bug was on screen?")

    assert [item.id for item in result.artifacts] == ["semantic"]


def test_vision_retrieval_enforces_result_and_context_limits(tmp_path: Path):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    artifacts = [
        artifact(
            f"artifact-{index}",
            message_id=f"message-{index}",
            visible_text=[f"qdrant_client traceback line {index} " + ("x" * 500)],
            created_at=datetime.now(timezone.utc) + timedelta(seconds=index),
        )
        for index in range(6)
    ]
    write_artifacts(service, "default", "conversation-a", artifacts)

    result = service.retrieve_relevant(
        "conversation-a",
        "qdrant_client traceback",
        limit=2,
        candidate_limit=3,
    )
    context = service.format_artifact_context(result.artifacts, max_chars=700)

    assert len(result.artifacts) == 2
    assert len(context) <= 700


def test_vision_retrieval_gracefully_ignores_corrupt_artifact_store(
    tmp_path: Path,
):
    service = VisionArtifactService(tmp_path / "vision", FakeVisionOllamaService())
    path = tmp_path / "vision" / "default" / "conversation-a.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")

    result = service.retrieve_relevant("conversation-a", "qdrant_client")

    assert result.artifacts == []
    assert result.warnings == []

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from app.schemas.chat import ChatImageAttachment
from app.schemas.vision import VisionEvidenceArtifact
from app.services.ollama_service import OllamaService


@dataclass(frozen=True)
class VisionAnalysisResult:
    artifacts: list[VisionEvidenceArtifact]
    warnings: list[str]


@dataclass(frozen=True)
class VisionRetrievalOptions:
    """Local retrieval knobs that keep the interface vector-search ready."""

    limit: int = 6
    candidate_limit: int = 24
    max_context_chars: int = 3_000


class VisionArtifactRetriever(Protocol):
    """Retriever boundary for future vector-backed image evidence search."""

    def retrieve(
        self,
        workspace_id: str | None,
        conversation_id: str | None,
        query: str,
        current_artifacts: list[VisionEvidenceArtifact],
        options: VisionRetrievalOptions,
    ) -> VisionAnalysisResult:
        """Return relevant artifacts without changing prompt assembly."""


class VisionArtifactService:
    """Persist and retrieve structured image evidence for conversations."""

    def __init__(
        self,
        storage_directory: Path,
        ollama_service: OllamaService,
    ) -> None:
        self.storage_directory = storage_directory.expanduser().resolve()
        self.ollama_service = ollama_service
        self._lock = Lock()

    async def analyze_images(
        self,
        conversation_id: str | None,
        message_id: str | None,
        images: list[ChatImageAttachment],
        vision_model: str | None,
        workspace_id: str | None = None,
    ) -> VisionAnalysisResult:
        workspace_id = self._clean_scope(workspace_id, "default")
        conversation_id = self._clean_scope(conversation_id, "default")
        message_id = self._clean_scope(message_id, "latest-user")
        if not images:
            return VisionAnalysisResult([], [])
        if not vision_model or vision_model == "none":
            return VisionAnalysisResult(
                [],
                ["Image evidence extraction skipped because no vision model is available."],
            )

        artifacts: list[VisionEvidenceArtifact] = []
        warnings: list[str] = []
        for index, image in enumerate(images, start=1):
            image_id = self._clean_scope(image.id, f"image-{index}")
            try:
                raw_response = await self.ollama_service.generate(
                    model=vision_model,
                    prompt=self._analysis_prompt(image.name),
                    images=[image.data],
                )
                payload = self._parse_json_object(raw_response)
                artifact = self._artifact_from_payload(
                    payload=payload,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    image_id=image_id,
                    image=image,
                    vision_model=vision_model,
                    status="succeeded",
                )
            except Exception as exc:
                warnings.append(
                    f"Image evidence extraction failed for {image.name}: {exc}"
                )
                artifact = self._artifact_from_payload(
                    payload={
                        "uncertainties": [
                            "Image evidence extraction failed; no structured "
                            "visual evidence is available for this image."
                        ]
                    },
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    image_id=image_id,
                    image=image,
                    vision_model=vision_model,
                    status="failed",
                )
            artifacts.append(artifact)

        if artifacts:
            self._append_artifacts(workspace_id, conversation_id, artifacts)
        return VisionAnalysisResult(artifacts, warnings)

    def retrieve_relevant(
        self,
        conversation_id: str | None,
        query: str,
        limit: int = 6,
        workspace_id: str | None = None,
        current_artifacts: list[VisionEvidenceArtifact] | None = None,
        candidate_limit: int = 24,
    ) -> VisionAnalysisResult:
        return self.retrieve(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query=query,
            current_artifacts=current_artifacts or [],
            options=VisionRetrievalOptions(
                limit=limit,
                candidate_limit=candidate_limit,
            ),
        )

    def retrieve(
        self,
        workspace_id: str | None,
        conversation_id: str | None,
        query: str,
        current_artifacts: list[VisionEvidenceArtifact],
        options: VisionRetrievalOptions,
    ) -> VisionAnalysisResult:
        workspace_id = self._clean_scope(workspace_id, "default")
        conversation_id = self._clean_scope(conversation_id, "default")
        artifacts = self._read_artifacts(workspace_id, conversation_id)

        current_by_id = {artifact.id: artifact for artifact in current_artifacts}
        warnings: list[str] = []
        if not artifacts and not current_artifacts:
            return VisionAnalysisResult([], warnings)

        query_profile = self._query_profile(query)
        scored: list[tuple[tuple[int, int, int, datetime], VisionEvidenceArtifact]] = []
        for artifact in artifacts:
            if artifact.id in current_by_id:
                continue
            if artifact.workspaceId != workspace_id or artifact.conversationId != conversation_id:
                continue
            text = self._artifact_search_text(artifact)
            profile = self._query_profile(text)
            exact_identifier_score = len(
                query_profile["identifiers"] & profile["identifiers"]
            )
            term_score = len(query_profile["terms"] & profile["terms"])
            semantic_score = len(query_profile["semantic"] & profile["semantic"])
            if exact_identifier_score <= 0 and term_score <= 0 and semantic_score <= 0:
                continue
            scored.append(
                (
                    (
                        exact_identifier_score,
                        term_score + semantic_score,
                        1 if artifact.status == "succeeded" else 0,
                        artifact.createdAt,
                    ),
                    artifact,
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        candidate_limit = max(options.limit, options.candidate_limit, len(current_artifacts))
        selected_prior = [
            artifact for _score, artifact in scored[:candidate_limit]
        ][: max(0, options.limit - len(current_artifacts))]
        selected = [
            *current_artifacts,
            *selected_prior,
        ][: max(1, options.limit)]
        return VisionAnalysisResult(
            selected,
            warnings,
        )

    def format_artifact_context(
        self,
        artifacts: list[VisionEvidenceArtifact],
        max_chars: int = 3_000,
    ) -> str:
        if not artifacts or max_chars <= 0:
            return ""
        lines = [
            "Structured image evidence:",
            (
                "A vision model extracted this evidence from uploaded images. "
                "Use it as visual evidence, but the primary text model must "
                "write the user-facing answer."
            ),
        ]
        used = sum(len(line) + 1 for line in lines)
        if used > max_chars:
            return "\n".join(lines)[:max_chars].rstrip()
        for index, artifact in enumerate(artifacts, start=1):
            block_lines = [
                f"Image artifact {index}: {artifact.imageName} ({artifact.imageId})",
                f"Status: {artifact.status}; messageId: {artifact.messageId}",
            ]
            block_lines.extend(self._labeled_lines("Visible text", artifact.visibleText))
            block_lines.extend(self._labeled_lines("Errors", artifact.errors))
            block_lines.extend(self._labeled_lines("File paths", artifact.filePaths))
            block_lines.extend(self._labeled_lines("Code", artifact.code))
            block_lines.extend(self._labeled_lines("UI elements", artifact.uiElements))
            block_lines.extend(self._labeled_lines("Observations", artifact.observations))
            block_lines.extend(self._labeled_lines("Uncertainties", artifact.uncertainties))
            block = "\n".join(block_lines)
            if used + len(block) + 2 > max_chars:
                remaining = max_chars - used - 2
                if remaining > 20:
                    lines.append(f"{block[: remaining - 14].rstrip()} [truncated]")
                break
            lines.append(block)
            used += len(block) + 2
        return "\n\n".join(lines)

    def _append_artifacts(
        self,
        workspace_id: str,
        conversation_id: str,
        artifacts: list[VisionEvidenceArtifact],
    ) -> None:
        with self._lock:
            existing = self._read_artifacts(workspace_id, conversation_id)
            by_id = {artifact.id: artifact for artifact in existing}
            for artifact in artifacts:
                by_id[artifact.id] = artifact
            path = self._conversation_file(workspace_id, conversation_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "workspaceId": workspace_id,
                        "conversationId": conversation_id,
                        "artifacts": [
                            artifact.model_dump(mode="json")
                            for artifact in by_id.values()
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    def _read_artifacts(
        self,
        workspace_id: str,
        conversation_id: str,
    ) -> list[VisionEvidenceArtifact]:
        path = self._conversation_file(workspace_id, conversation_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw_artifacts = payload.get("artifacts", [])
            if not isinstance(raw_artifacts, list):
                return []
            artifacts = [
                VisionEvidenceArtifact.model_validate(item)
                for item in raw_artifacts
            ]
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError):
            return []
        return artifacts

    def _artifact_from_payload(
        self,
        payload: dict[str, Any],
        workspace_id: str,
        conversation_id: str,
        message_id: str,
        image_id: str,
        image: ChatImageAttachment,
        vision_model: str,
        status: str,
    ) -> VisionEvidenceArtifact:
        artifact_id = str(
            uuid5(
                NAMESPACE_URL,
                f"vision:{conversation_id}:{message_id}:{image_id}",
            )
        )
        return VisionEvidenceArtifact(
            id=artifact_id,
            workspaceId=workspace_id,
            conversationId=conversation_id,
            messageId=message_id,
            imageId=image_id,
            imageName=image.name,
            mimeType=image.mimeType,
            visionModel=vision_model,
            createdAt=datetime.now(timezone.utc),
            status=status,
            visibleText=self._string_list(payload.get("visibleText")),
            errors=self._string_list(payload.get("errors")),
            filePaths=self._string_list(payload.get("filePaths")),
            code=self._string_list(payload.get("code")),
            uiElements=self._string_list(payload.get("uiElements")),
            observations=self._string_list(payload.get("observations")),
            uncertainties=self._string_list(payload.get("uncertainties")),
        )

    @staticmethod
    def _analysis_prompt(image_name: str) -> str:
        return (
            "You extract structured visual evidence from an image for a local "
            "coding assistant.\n"
            "Return JSON only with this exact shape:\n"
            '{"visibleText":[],"errors":[],"filePaths":[],"code":[],'
            '"uiElements":[],"observations":[],"uncertainties":[]}\n'
            "Rules:\n"
            "- Preserve visible text, code, identifiers, paths, numbers, and "
            "error messages exactly as seen.\n"
            "- Do not write a caption or user-facing answer.\n"
            "- Put uncertainty in uncertainties instead of guessing.\n"
            "- If there is no evidence for a field, return an empty array.\n\n"
            f"Image name: {image_name}"
        )

    @staticmethod
    def _parse_json_object(raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("vision model did not return JSON")
            payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("vision model returned non-object JSON")
        return payload

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip()[:4_000])
        return items[:20]

    @staticmethod
    def _terms(text: str) -> set[str]:
        terms: set[str] = set()
        for term in re.findall(r"[A-Za-z0-9_.:/-]{3,}", text.lower()):
            normalized = term.strip(".,:;!?()[]{}\"'")
            if normalized:
                terms.add(normalized)
        return terms

    @classmethod
    def _query_profile(cls, text: str) -> dict[str, set[str]]:
        terms = cls._terms(text)
        identifiers = {
            term
            for term in terms
            if any(character in term for character in "._:/-")
            or any(character.isdigit() for character in term)
        }
        semantic = set(terms)
        for term in list(terms):
            semantic.update(SEMANTIC_ALIASES.get(term, ()))
        return {
            "terms": terms,
            "identifiers": identifiers,
            "semantic": semantic,
        }

    @staticmethod
    def _artifact_search_text(artifact: VisionEvidenceArtifact) -> str:
        return "\n".join(
            [
                artifact.imageName,
                *artifact.visibleText,
                *artifact.errors,
                *artifact.filePaths,
                *artifact.code,
                *artifact.uiElements,
                *artifact.observations,
                *artifact.uncertainties,
            ]
        )

    @staticmethod
    def _labeled_lines(label: str, values: list[str]) -> list[str]:
        if not values:
            return []
        return [f"{label}:"] + [f"- {value}" for value in values]

    def _conversation_file(self, workspace_id: str, conversation_id: str) -> Path:
        return self.storage_directory / workspace_id / f"{conversation_id}.json"

    @staticmethod
    def _clean_scope(value: str | None, fallback: str) -> str:
        text = re.sub(r"[^A-Za-z0-9_.:-]+", "-", (value or "").strip())
        return text[:160] or fallback


SEMANTIC_ALIASES: dict[str, tuple[str, ...]] = {
    "bug": ("error", "exception", "failure", "traceback"),
    "crash": ("error", "exception", "failure", "traceback"),
    "error": ("bug", "exception", "failure", "traceback"),
    "exception": ("bug", "error", "failure", "traceback"),
    "failure": ("bug", "error", "exception", "traceback"),
    "screen": ("screenshot", "image", "ui"),
    "screenshot": ("screen", "image", "ui"),
    "image": ("screen", "screenshot", "ui"),
    "path": ("file", "filename", "directory"),
    "file": ("path", "filename", "directory"),
    "filename": ("file", "path", "directory"),
    "button": ("ui", "control", "element"),
    "control": ("ui", "button", "element"),
    "element": ("ui", "button", "control"),
    "code": ("source", "snippet", "identifier"),
    "source": ("code", "snippet", "identifier"),
}

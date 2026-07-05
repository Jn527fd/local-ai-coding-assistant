from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.services.document_service import DocumentService
from app.services.job_service import JobService
from app.services.redaction import redact_diagnostics


class DiagnosticsService:
    """Build safe metadata-only diagnostics for local operation."""

    def __init__(
        self,
        *,
        settings: Settings,
        document_service: DocumentService,
        job_service: JobService,
        model_manager: Any,
        vector_store_manager: Any,
    ) -> None:
        self.settings = settings
        self.document_service = document_service
        self.job_service = job_service
        self.model_manager = model_manager
        self.vector_store_manager = vector_store_manager

    async def status(self) -> dict[str, Any]:
        payload = {
            "generatedAt": self._now(),
            "runtime": self._runtime_status(),
            "models": await self._model_status(),
            "documents": self._document_status(),
            "retrieval": self._retrieval_status(),
            "jobs": self._job_status(),
            "warnings": [],
        }
        return redact_diagnostics(payload)

    async def support_bundle(self) -> dict[str, Any]:
        payload = {
            "bundleVersion": 1,
            "generatedAt": self._now(),
            "redaction": {
                "mode": "metadata-only",
                "contentIncluded": False,
                "secretsIncluded": False,
                "privatePathsIncluded": False,
            },
            "diagnostics": await self.status(),
        }
        return redact_diagnostics(payload)

    def _runtime_status(self) -> dict[str, Any]:
        return {
            "appName": self.settings.app_name,
            "appVersion": self.settings.app_version,
            "environment": self.settings.app_environment,
            "debug": self.settings.app_debug,
            "browserCredentialSecure": self.settings.session_cookie_secure,
            "persistentLoginConfigured": bool(
                self.settings.session_signing_key.get_secret_value()
            ),
            "vectorStoreBackend": self.settings.vector_store_backend,
            "metadataDatabaseConfigured": self.settings.metadata_database_file
            is not None,
        }

    async def _model_status(self) -> dict[str, Any]:
        try:
            status = await self.model_manager.status()
        except Exception as exc:
            return {
                "available": False,
                "ollamaConnected": False,
                "error": str(exc),
            }
        return {
            "available": True,
            "ollamaConnected": bool(status.get("ollama_connected")),
            "activeModel": status.get("active_model") or "",
            "installedModelCount": len(status.get("installed_models") or []),
            "supportedModelCount": len(status.get("supported_models") or []),
            "phase": status.get("phase") or "unknown",
            "warning": status.get("warning") or "",
            "error": status.get("error") or "",
        }

    def _document_status(self) -> dict[str, Any]:
        status_counts: Counter[str] = Counter()
        warning_count = 0
        error_count = 0
        chunk_count = 0
        conversation_count = 0
        root = self.document_service.upload_directory
        if not root.exists():
            return {
                "conversationCount": 0,
                "documentCount": 0,
                "statusCounts": {},
                "chunkCount": 0,
                "warningCount": 0,
                "errorCount": 0,
            }

        for conversation_dir in root.iterdir():
            if not conversation_dir.is_dir():
                continue
            conversation_count += 1
            for document_dir in conversation_dir.iterdir():
                if not document_dir.is_dir():
                    continue
                metadata_path = document_dir / "metadata.json"
                if not metadata_path.exists():
                    status_counts["missing_metadata"] += 1
                    continue
                try:
                    metadata = self.document_service._read_json(metadata_path)
                except Exception:
                    status_counts["unreadable_metadata"] += 1
                    error_count += 1
                    continue
                status_counts[str(metadata.get("status") or "unknown")] += 1
                warning_count += len(metadata.get("extractionWarnings") or [])
                if metadata.get("error"):
                    error_count += 1
                chunk_count += int(metadata.get("chunkCount") or 0)

        return {
            "conversationCount": conversation_count,
            "documentCount": sum(status_counts.values()),
            "statusCounts": dict(sorted(status_counts.items())),
            "chunkCount": chunk_count,
            "warningCount": warning_count,
            "errorCount": error_count,
        }

    def _retrieval_status(self) -> dict[str, Any]:
        diagnostics = self.vector_store_manager.diagnostics()
        return {
            "defaultBackend": diagnostics.get("defaultBackend"),
            "selectedBackend": diagnostics.get("selectedBackend"),
            "fallbackUsed": diagnostics.get("fallbackUsed"),
            "backends": diagnostics.get("backends", []),
            "ragTopK": self.settings.rag_top_k,
            "ragCandidateK": self.settings.rag_candidate_k,
            "rerankerMaxCandidates": self.settings.reranker_max_candidates,
            "compressionBudgetChars": (
                self.settings.context_compression_max_prompt_chars
            ),
        }

    def _job_status(self) -> dict[str, Any]:
        jobs = self.job_service.list(limit=200)
        state_counts = Counter(job.state for job in jobs)
        type_counts = Counter(job.type for job in jobs)
        latest_failures = [
            {
                "type": job.type,
                "state": job.state,
                "error": job.error or "",
                "updatedAt": job.updatedAt,
            }
            for job in jobs
            if job.state == "failed"
        ][:5]
        return {
            "recentJobCount": len(jobs),
            "stateCounts": dict(sorted(state_counts.items())),
            "typeCounts": dict(sorted(type_counts.items())),
            "latestFailures": latest_failures,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

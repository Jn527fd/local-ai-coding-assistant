from dataclasses import dataclass
from typing import Any

from app.schemas.chat import ConversationSettings
from app.services.component_registry import CAPABILITY_KEYS, ComponentRegistry


SETTING_CATEGORIES = {
    "llmModel": "llmModels",
    "embedderModel": "embedderModels",
    "ocrEngine": "ocrEngines",
    "pdfParser": "pdfParsers",
    "chunker": "chunkers",
    "vectorDatabase": "vectorDatabases",
    "ragPipeline": "ragPipelines",
    "reranker": "rerankerModels",
    "contextCompressor": "contextCompressors",
    "visionModel": "visionModels",
}

OPTIONAL_DEFAULTS = {
    "embedderModel": "",
    "ocrEngine": "none",
    "pdfParser": "none",
    "chunker": "recursive",
    "vectorDatabase": "qdrant",
    "ragPipeline": "basic",
    "reranker": "none",
    "contextCompressor": "auto",
    "visionModel": "none",
}

DISABLED_SELECTIONS = {"", "none"}


@dataclass(frozen=True)
class ResolvedComponent:
    """Validation and fallback details for one selected AI component."""

    setting_key: str
    category: str
    requested_id: str
    resolved_id: str
    valid: bool
    available: bool
    required: bool
    source: str | None = None
    reason: str | None = None
    capability: dict[str, Any] | None = None


@dataclass(frozen=True)
class AIExecutionContext:
    """Resolved component selections for one backend execution."""

    conversation_id: str | None
    conversation_settings: ConversationSettings
    resolved_llm_model: str
    resolved_embedder_model: str | None
    resolved_ocr_engine: str
    resolved_pdf_parser: str
    resolved_chunker: str
    resolved_vector_database: str
    resolved_rag_pipeline: str
    resolved_reranker: str
    resolved_context_compressor: str
    resolved_vision_model: str
    capabilities_snapshot: dict[str, list[dict[str, Any]]]
    components: dict[str, ResolvedComponent]


class AISettingsResolver:
    """Resolve browser-local conversation settings against local capabilities."""

    def __init__(self, component_registry: ComponentRegistry) -> None:
        self.component_registry = component_registry

    async def resolve(
        self,
        conversation_settings: ConversationSettings | None,
        active_model: str,
        conversation_id: str | None = None,
    ) -> AIExecutionContext:
        capabilities = self._normalize_capabilities(
            await self.component_registry.capabilities()
        )
        normalized_settings = self._normalize_settings(
            conversation_settings=conversation_settings,
            active_model=active_model,
            capabilities=capabilities,
        )

        llm_component = self._resolve_llm(
            settings=normalized_settings,
            active_model=active_model,
            capabilities=capabilities,
        )
        components = {
            "llmModel": llm_component,
            "embedderModel": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="embedderModel",
                capabilities=capabilities,
                fallback="",
                allow_disabled=True,
                disabled_resolved_id="",
            ),
            "ocrEngine": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="ocrEngine",
                capabilities=capabilities,
                fallback="none",
                allow_disabled=True,
                disabled_resolved_id="none",
            ),
            "pdfParser": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="pdfParser",
                capabilities=capabilities,
                fallback=self._first_available_id(capabilities, "pdfParsers")
                or "none",
                allow_disabled=True,
                disabled_resolved_id="none",
            ),
            "chunker": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="chunker",
                capabilities=capabilities,
                fallback="recursive",
            ),
            "vectorDatabase": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="vectorDatabase",
                capabilities=capabilities,
                fallback="qdrant",
            ),
            "ragPipeline": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="ragPipeline",
                capabilities=capabilities,
                fallback="basic",
            ),
            "reranker": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="reranker",
                capabilities=capabilities,
                fallback="none",
                allow_disabled=True,
                disabled_resolved_id="none",
            ),
            "contextCompressor": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="contextCompressor",
                capabilities=capabilities,
                fallback="auto",
                allow_disabled=True,
                disabled_resolved_id="auto",
            ),
            "visionModel": self._resolve_optional_component(
                settings=normalized_settings,
                setting_key="visionModel",
                capabilities=capabilities,
                fallback="none",
                allow_disabled=True,
                disabled_resolved_id="none",
            ),
        }

        return AIExecutionContext(
            conversation_id=conversation_id,
            conversation_settings=normalized_settings,
            resolved_llm_model=llm_component.resolved_id,
            resolved_embedder_model=(
                components["embedderModel"].resolved_id or None
            ),
            resolved_ocr_engine=components["ocrEngine"].resolved_id,
            resolved_pdf_parser=components["pdfParser"].resolved_id,
            resolved_chunker=components["chunker"].resolved_id,
            resolved_vector_database=components["vectorDatabase"].resolved_id,
            resolved_rag_pipeline=components["ragPipeline"].resolved_id,
            resolved_reranker=components["reranker"].resolved_id,
            resolved_context_compressor=components[
                "contextCompressor"
            ].resolved_id,
            resolved_vision_model=components["visionModel"].resolved_id,
            capabilities_snapshot=capabilities,
            components=components,
        )

    def _normalize_settings(
        self,
        conversation_settings: ConversationSettings | None,
        active_model: str,
        capabilities: dict[str, list[dict[str, Any]]],
    ) -> ConversationSettings:
        values = {
            key: self._clean_selection(
                getattr(conversation_settings, key, None)
            )
            for key in SETTING_CATEGORIES
        }
        values["llmModel"] = values["llmModel"] or active_model

        for key, fallback in OPTIONAL_DEFAULTS.items():
            if values[key]:
                continue
            if key == "embedderModel":
                values[key] = (
                    self._preferred_embedder(capabilities)
                    or self._first_available_id(capabilities, "embedderModels")
                    or fallback
                )
                continue
            if key == "pdfParser":
                values[key] = (
                    self._preferred_available_id(
                        capabilities,
                        "pdfParsers",
                        ["docling"],
                    )
                    or fallback
                )
                continue
            if key == "ocrEngine":
                values[key] = (
                    self._preferred_available_id(
                        capabilities,
                        "ocrEngines",
                        ["paddleocr"],
                    )
                    or fallback
                )
                continue
            values[key] = fallback

        return ConversationSettings(**values)

    def _resolve_llm(
        self,
        settings: ConversationSettings,
        active_model: str,
        capabilities: dict[str, list[dict[str, Any]]],
    ) -> ResolvedComponent:
        selected = self._clean_selection(settings.llmModel)
        capability = self._capability_by_id(
            capabilities,
            "llmModels",
            selected,
        )
        if capability is not None and self._is_available(capability):
            return self._valid_component(
                setting_key="llmModel",
                category="llmModels",
                selected=selected,
                capability=capability,
                required=True,
            )

        if selected == active_model:
            return ResolvedComponent(
                setting_key="llmModel",
                category="llmModels",
                requested_id=selected,
                resolved_id=active_model,
                valid=True,
                available=True,
                required=True,
                source="global-active-model",
                reason="using global active model",
            )

        reason = "model is unavailable"
        if capability is None:
            reason = "model is not an available LLM capability"
        return ResolvedComponent(
            setting_key="llmModel",
            category="llmModels",
            requested_id=selected,
            resolved_id=active_model,
            valid=False,
            available=False,
            required=True,
            source=(
                str(capability.get("source"))
                if capability and capability.get("source") is not None
                else None
            ),
            reason=reason,
            capability=capability,
        )

    def _resolve_optional_component(
        self,
        settings: ConversationSettings,
        setting_key: str,
        capabilities: dict[str, list[dict[str, Any]]],
        fallback: str,
        allow_disabled: bool = False,
        disabled_resolved_id: str | None = None,
    ) -> ResolvedComponent:
        category = SETTING_CATEGORIES[setting_key]
        selected = self._clean_selection(getattr(settings, setting_key))
        if setting_key == "contextCompressor":
            return ResolvedComponent(
                setting_key=setting_key,
                category=category,
                requested_id=selected or "auto",
                resolved_id="auto",
                valid=True,
                available=True,
                required=False,
                source="builtin",
                reason="context management is automatic",
            )
        if allow_disabled and selected in DISABLED_SELECTIONS:
            return ResolvedComponent(
                setting_key=setting_key,
                category=category,
                requested_id=selected,
                resolved_id=(
                    disabled_resolved_id
                    if disabled_resolved_id is not None
                    else fallback
                ),
                valid=True,
                available=True,
                required=False,
                source="builtin",
                reason="component disabled",
            )

        capability = self._capability_by_id(capabilities, category, selected)
        if capability is not None and self._is_available(capability):
            return self._valid_component(
                setting_key=setting_key,
                category=category,
                selected=selected,
                capability=capability,
                required=False,
            )

        reason = "component is unavailable"
        if capability is None:
            reason = "component is not a known capability"
        return ResolvedComponent(
            setting_key=setting_key,
            category=category,
            requested_id=selected,
            resolved_id=fallback,
            valid=False,
            available=False,
            required=False,
            source=(
                str(capability.get("source"))
                if capability and capability.get("source") is not None
                else None
            ),
            reason=reason,
            capability=capability,
        )

    def _valid_component(
        self,
        setting_key: str,
        category: str,
        selected: str,
        capability: dict[str, Any],
        required: bool,
    ) -> ResolvedComponent:
        return ResolvedComponent(
            setting_key=setting_key,
            category=category,
            requested_id=selected,
            resolved_id=selected,
            valid=True,
            available=True,
            required=required,
            source=(
                str(capability.get("source"))
                if capability.get("source") is not None
                else None
            ),
            capability=capability,
        )

    @staticmethod
    def _normalize_capabilities(
        capabilities: dict[str, list[dict[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            key: list(capabilities.get(key, []))
            for key in CAPABILITY_KEYS
        }

    @staticmethod
    def _clean_selection(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    def _preferred_embedder(
        self,
        capabilities: dict[str, list[dict[str, Any]]],
    ) -> str:
        available_ids = {
            self._capability_id(item)
            for item in capabilities["embedderModels"]
            if self._is_available(item)
        }
        for preferred in ("nomic-embed-text", "nomic-embed-text:latest"):
            if preferred in available_ids:
                return preferred
        return ""

    def _first_available_id(
        self,
        capabilities: dict[str, list[dict[str, Any]]],
        category: str,
    ) -> str:
        for item in capabilities[category]:
            if self._is_available(item):
                return self._capability_id(item)
        return ""

    def _preferred_available_id(
        self,
        capabilities: dict[str, list[dict[str, Any]]],
        category: str,
        preferred_ids: list[str],
    ) -> str:
        for preferred_id in preferred_ids:
            capability = self._capability_by_id(
                capabilities,
                category,
                preferred_id,
            )
            if capability is not None and self._is_available(capability):
                return preferred_id
        return self._first_available_id(capabilities, category)

    def _capability_by_id(
        self,
        capabilities: dict[str, list[dict[str, Any]]],
        category: str,
        capability_id: str,
    ) -> dict[str, Any] | None:
        for item in capabilities[category]:
            if self._capability_id(item) == capability_id:
                return item
        return None

    @staticmethod
    def _capability_id(capability: dict[str, Any]) -> str:
        capability_id = capability.get("id") or capability.get("name") or ""
        return str(capability_id)

    @staticmethod
    def _is_available(capability: dict[str, Any]) -> bool:
        return capability.get("available") is True

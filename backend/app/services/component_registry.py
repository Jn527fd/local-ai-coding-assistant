from collections.abc import Iterable
from importlib.util import find_spec
import shutil
from typing import Any

from app.ai.vectorstores import VectorStoreManager
from app.services.ollama_service import (
    InstalledOllamaModel,
    OllamaService,
    OllamaServiceError,
)

CAPABILITY_KEYS = [
    "llmModels",
    "embedderModels",
    "rerankerModels",
    "visionModels",
    "ocrEngines",
    "pdfParsers",
    "chunkers",
    "vectorDatabases",
    "ragPipelines",
    "contextCompressors",
    "unknownOllamaModels",
]

EMBEDDER_MODEL_MARKERS = (
    "embed",
    "embedding",
    "nomic-embed",
    "mxbai-embed",
    "bge-m3",
    "all-minilm",
    "snowflake-arctic-embed",
)

RERANKER_MODEL_MARKERS = (
    "rerank",
    "reranker",
    "bge-reranker",
    "qwen3-reranker",
)

VISION_MODEL_MARKERS = (
    "vision",
    "vl",
    "llava",
    "minicpm-v",
    "qwen2.5vl",
    "qwen3-vl",
    "granite3.2-vision",
)

CAPABILITY_STATUS_IMPLEMENTED = "implemented"
CAPABILITY_STATUS_FALLBACK = "fallback"
CAPABILITY_STATUS_PLACEHOLDER = "placeholder"
CAPABILITY_STATUS_DISCOVERY_ONLY = "discovery-only"
CAPABILITY_STATUS_UNAVAILABLE = "unavailable"

STATIC_CAPABILITY_METADATA = {
    "chunker": {
        "fixed": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Splits documents into fixed-size character windows.",
        ),
        "recursive": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Splits documents on paragraph-aware recursive boundaries.",
        ),
        "semantic": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently falls back to recursive chunking.",
        ),
        "document-aware": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently falls back to recursive chunking.",
        ),
    },
    "vectorDatabase": {
        "chroma": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Optional Chroma adapter is unavailable; vectors use the local JSON index.",
        ),
        "faiss": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Selection is recorded; vectors are stored in the local JSON index.",
        ),
        "qdrant": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Selection is recorded; vectors are stored in the local JSON index.",
        ),
        "lancedb": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Selection is recorded; vectors are stored in the local JSON index.",
        ),
    },
    "ragPipeline": {
        "basic": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Uses local vector retrieval when document RAG is enabled.",
        ),
        "hybrid": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Uses local vector retrieval; keyword/vector fusion is not separate yet.",
        ),
        "reranked": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Retrieves candidate chunks and reranks them when a reranker is selected.",
        ),
        "graph": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently uses the local retrieval path.",
        ),
        "agentic": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently uses the local retrieval path.",
        ),
    },
    "contextCompressor": {
        "none": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Leaves chat history and retrieved context unchanged.",
        ),
        "summarizer": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Summarizes older chat history with the active LLM when needed.",
        ),
        "semantic": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently falls back to token compression.",
        ),
        "token": (
            CAPABILITY_STATUS_IMPLEMENTED,
            True,
            "Deterministically trims older history and retrieved context to budget.",
        ),
        "memory": (
            CAPABILITY_STATUS_FALLBACK,
            False,
            "Accepted by settings, but currently falls back to summarizer or token compression.",
        ),
    },
}


def contains_marker(name: str, markers: Iterable[str]) -> bool:
    return any(marker in name for marker in markers)


def classify_ollama_model(model: InstalledOllamaModel) -> tuple[str, str]:
    """Return the capabilities category and type for an installed Ollama model."""

    normalized_name = model.name.lower()
    if contains_marker(normalized_name, EMBEDDER_MODEL_MARKERS):
        return "embedderModels", "embedderModel"
    if contains_marker(normalized_name, RERANKER_MODEL_MARKERS):
        return "rerankerModels", "rerankerModel"
    if contains_marker(normalized_name, VISION_MODEL_MARKERS):
        return "visionModels", "visionModel"
    if model.name:
        return "llmModels", "llmModel"
    return "unknownOllamaModels", "unknownOllamaModel"


class ComponentRegistry:
    """Discover local AI-adjacent capabilities without changing runtime behavior."""

    def __init__(
        self,
        ollama_service: OllamaService,
        vector_store_manager: VectorStoreManager | None = None,
    ) -> None:
        self.ollama_service = ollama_service
        self.vector_store_manager = vector_store_manager

    async def capabilities(self) -> dict[str, list[dict[str, Any]]]:
        """Return a categorized, frontend-friendly capabilities object."""

        capabilities: dict[str, list[dict[str, Any]]] = {
            key: [] for key in CAPABILITY_KEYS
        }
        capabilities["ocrEngines"] = self._ocr_engines()
        capabilities["pdfParsers"] = self._pdf_parsers()
        capabilities["chunkers"] = self._static_capabilities(
            "chunker",
            ("fixed", "recursive", "semantic", "document-aware"),
        )
        capabilities["vectorDatabases"] = self._vector_databases()
        capabilities["ragPipelines"] = self._static_capabilities(
            "ragPipeline",
            ("basic", "hybrid", "reranked", "graph", "agentic"),
        )
        capabilities["contextCompressors"] = self._static_capabilities(
            "contextCompressor",
            ("none", "summarizer", "semantic", "token", "memory"),
        )

        try:
            installed_models = await self.ollama_service.list_installed_models()
        except OllamaServiceError:
            installed_models = []

        for model in installed_models:
            category, capability_type = self._classify_ollama_model(model)
            capabilities[category].append(
                self._ollama_model_capability(model, category, capability_type)
            )

        for key in (
            "llmModels",
            "embedderModels",
            "rerankerModels",
            "visionModels",
            "unknownOllamaModels",
        ):
            capabilities[key].sort(key=lambda item: item["name"].lower())

        return capabilities

    def _classify_ollama_model(
        self,
        model: InstalledOllamaModel,
    ) -> tuple[str, str]:
        return classify_ollama_model(model)

    def _ollama_model_capability(
        self,
        model: InstalledOllamaModel,
        category: str,
        capability_type: str,
    ) -> dict[str, Any]:
        details = {
            "parameterSize": model.parameter_size or None,
            "parametersBillion": model.parameters_billion,
            "family": model.family,
            "quantizationLevel": model.quantization_level,
        }
        capability = {
            "id": model.name,
            "label": model.name,
            "type": capability_type,
            "available": True,
            "source": "ollama",
            "name": model.name,
            "size": model.size_bytes,
            "sizeBytes": model.size_bytes,
            "modifiedAt": model.modified_at,
            "details": details,
        }
        if category in {"visionModels", "unknownOllamaModels"}:
            return self._with_execution_metadata(
                capability,
                status=CAPABILITY_STATUS_DISCOVERY_ONLY,
                implemented=False,
                description=(
                    "Model is discoverable through Ollama, but this capability "
                    "does not have an execution path in the app yet."
                ),
            )
        return self._with_execution_metadata(
            capability,
            status=CAPABILITY_STATUS_IMPLEMENTED,
            implemented=True,
            description="Model can be used through the local Ollama provider.",
        )

    def _ocr_engines(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "none",
                "label": "None",
                "type": "ocrEngine",
                "available": True,
                "source": "builtin",
                "implementationStatus": CAPABILITY_STATUS_IMPLEMENTED,
                "implemented": True,
                "execution": {
                    "status": CAPABILITY_STATUS_IMPLEMENTED,
                    "implemented": True,
                    "mode": "disabled",
                    "description": "Disables OCR for document processing.",
                },
            },
            self._local_tool_capability(
                capability_id="tesseract",
                label="Tesseract",
                capability_type="ocrEngine",
                binaries=("tesseract",),
            ),
            self._local_tool_capability(
                capability_id="ocrmypdf",
                label="OCRmyPDF",
                capability_type="ocrEngine",
                binaries=("ocrmypdf",),
                available_status=CAPABILITY_STATUS_IMPLEMENTED,
                available_implemented=True,
                available_description=(
                    "Runs OCRmyPDF for low-text PDFs and extracts the OCR text."
                ),
            ),
            self._local_tool_capability(
                capability_id="paddleocr",
                label="PaddleOCR",
                capability_type="ocrEngine",
                packages=("paddleocr",),
            ),
            self._local_tool_capability(
                capability_id="easyocr",
                label="EasyOCR",
                capability_type="ocrEngine",
                packages=("easyocr",),
            ),
            self._local_tool_capability(
                capability_id="docling",
                label="Docling",
                capability_type="ocrEngine",
                packages=("docling",),
            ),
        ]

    def _pdf_parsers(self) -> list[dict[str, Any]]:
        return [
            self._local_tool_capability(
                capability_id="pymupdf",
                label="PyMuPDF",
                capability_type="pdfParser",
                packages=("fitz", "pymupdf"),
                available_status=CAPABILITY_STATUS_IMPLEMENTED,
                available_implemented=True,
                available_description="Extracts selectable PDF text with PyMuPDF.",
            ),
            self._local_tool_capability(
                capability_id="pdfplumber",
                label="pdfplumber",
                capability_type="pdfParser",
                packages=("pdfplumber",),
                available_status=CAPABILITY_STATUS_IMPLEMENTED,
                available_implemented=True,
                available_description="Extracts selectable PDF text with pdfplumber.",
            ),
            self._local_tool_capability(
                capability_id="docling",
                label="Docling",
                capability_type="pdfParser",
                packages=("docling",),
            ),
        ]

    def _vector_databases(self) -> list[dict[str, Any]]:
        capabilities = self._static_capabilities(
            "vectorDatabase",
            ("chroma", "faiss", "qdrant", "lancedb"),
        )
        health_items = (
            self.vector_store_manager.health()
            if self.vector_store_manager
            else []
        )
        health_by_id = {item.id: item for item in health_items}
        json_health = health_by_id.get("json")
        for capability in capabilities:
            if capability["id"] == "chroma":
                chroma_health = health_by_id.get("chroma")
                if chroma_health and chroma_health.available:
                    self._with_execution_metadata(
                        capability,
                        status=CAPABILITY_STATUS_IMPLEMENTED,
                        implemented=True,
                        description=chroma_health.description,
                    )
                    capability["source"] = chroma_health.source
                    capability["checks"] = chroma_health.checks
                    capability["adapter"] = {
                        "id": chroma_health.id,
                        "mode": chroma_health.mode,
                    }
                elif chroma_health:
                    capability["checks"] = chroma_health.checks
                    capability["adapter"] = {
                        "id": chroma_health.id,
                        "mode": chroma_health.mode,
                    }
            capability["fallbackStore"] = "json"
            if json_health:
                capability["fallbackAvailable"] = json_health.available
        return capabilities

    def _static_capabilities(
        self,
        capability_type: str,
        capability_ids: Iterable[str],
    ) -> list[dict[str, Any]]:
        capabilities = []
        for capability_id in capability_ids:
            status, implemented, description = self._static_capability_metadata(
                capability_type,
                capability_id,
            )
            capabilities.append(
                self._with_execution_metadata(
                    {
                        "id": capability_id,
                        "label": self._label_from_id(capability_id),
                        "type": capability_type,
                        "available": True,
                        "source": "static",
                    },
                    status=status,
                    implemented=implemented,
                    description=description,
                )
            )
        return capabilities

    def _local_tool_capability(
        self,
        capability_id: str,
        label: str,
        capability_type: str,
        packages: Iterable[str] = (),
        binaries: Iterable[str] = (),
        available_status: str = CAPABILITY_STATUS_DISCOVERY_ONLY,
        available_implemented: bool = False,
        available_description: str | None = None,
    ) -> dict[str, Any]:
        checks = [
            {
                "type": "pythonPackage",
                "name": package,
                "available": self._python_package_available(package),
            }
            for package in packages
        ]
        checks.extend(
            {
                "type": "binary",
                "name": binary,
                "available": shutil.which(binary) is not None,
            }
            for binary in binaries
        )
        available = any(check["available"] for check in checks)
        status = (
            available_status
            if available
            else CAPABILITY_STATUS_UNAVAILABLE
        )
        implemented = available and available_implemented
        return self._with_execution_metadata(
            {
                "id": capability_id,
                "label": label,
                "type": capability_type,
                "available": available,
                "source": "local",
                "checks": checks,
            },
            status=status,
            implemented=implemented,
            description=(
                available_description
                if available and available_description
                else "Tool was not detected in the backend runtime."
                if not available
                else (
                    "Tool is detected for capability selection, but full "
                    "execution is not wired for this capability yet."
                )
            ),
        )

    def _with_execution_metadata(
        self,
        capability: dict[str, Any],
        status: str,
        implemented: bool,
        description: str,
    ) -> dict[str, Any]:
        capability["implementationStatus"] = status
        capability["implemented"] = implemented
        capability["execution"] = {
            "status": status,
            "implemented": implemented,
            "mode": self._execution_mode(status),
            "description": description,
        }
        return capability

    def _static_capability_metadata(
        self,
        capability_type: str,
        capability_id: str,
    ) -> tuple[str, bool, str]:
        return STATIC_CAPABILITY_METADATA.get(capability_type, {}).get(
            capability_id,
            (
                CAPABILITY_STATUS_PLACEHOLDER,
                False,
                "Static option is exposed for compatibility with future phases.",
            ),
        )

    @staticmethod
    def _execution_mode(status: str) -> str:
        if status == CAPABILITY_STATUS_IMPLEMENTED:
            return "direct"
        if status == CAPABILITY_STATUS_FALLBACK:
            return "fallback"
        if status == CAPABILITY_STATUS_DISCOVERY_ONLY:
            return "discovery"
        if status == CAPABILITY_STATUS_UNAVAILABLE:
            return "unavailable"
        return "placeholder"

    @staticmethod
    def _python_package_available(package_name: str) -> bool:
        try:
            return find_spec(package_name) is not None
        except (ImportError, AttributeError, ValueError):
            return False

    @staticmethod
    def _label_from_id(capability_id: str) -> str:
        return capability_id.replace("-", " ").title()

from collections.abc import Iterable
from importlib.util import find_spec
import shutil
from typing import Any

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

    def __init__(self, ollama_service: OllamaService) -> None:
        self.ollama_service = ollama_service

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
        capabilities["vectorDatabases"] = self._static_capabilities(
            "vectorDatabase",
            ("chroma", "faiss", "qdrant", "lancedb"),
        )
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
                self._ollama_model_capability(model, capability_type)
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
        capability_type: str,
    ) -> dict[str, Any]:
        details = {
            "parameterSize": model.parameter_size or None,
            "parametersBillion": model.parameters_billion,
            "family": model.family,
            "quantizationLevel": model.quantization_level,
        }
        return {
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

    def _ocr_engines(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "none",
                "label": "None",
                "type": "ocrEngine",
                "available": True,
                "source": "builtin",
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
                packages=("ocrmypdf",),
                binaries=("ocrmypdf",),
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
            ),
            self._local_tool_capability(
                capability_id="pdfplumber",
                label="pdfplumber",
                capability_type="pdfParser",
                packages=("pdfplumber",),
            ),
            self._local_tool_capability(
                capability_id="docling",
                label="Docling",
                capability_type="pdfParser",
                packages=("docling",),
            ),
        ]

    def _static_capabilities(
        self,
        capability_type: str,
        capability_ids: Iterable[str],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": capability_id,
                "label": self._label_from_id(capability_id),
                "type": capability_type,
                "available": True,
                "source": "static",
            }
            for capability_id in capability_ids
        ]

    def _local_tool_capability(
        self,
        capability_id: str,
        label: str,
        capability_type: str,
        packages: Iterable[str] = (),
        binaries: Iterable[str] = (),
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
        return {
            "id": capability_id,
            "label": label,
            "type": capability_type,
            "available": any(check["available"] for check in checks),
            "source": "local",
            "checks": checks,
        }

    @staticmethod
    def _python_package_available(package_name: str) -> bool:
        try:
            return find_spec(package_name) is not None
        except (ImportError, AttributeError, ValueError):
            return False

    @staticmethod
    def _label_from_id(capability_id: str) -> str:
        return capability_id.replace("-", " ").title()

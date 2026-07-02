from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class OCREngineError(RuntimeError):
    """Base error for optional OCR execution."""


class OCREngineUnavailableError(OCREngineError):
    """Raised when a selected OCR engine is not installed or configured."""


class OCREngineExecutionError(OCREngineError):
    """Raised when an installed OCR engine fails to process a document."""


@dataclass(frozen=True)
class OCRResult:
    """Text and warnings produced by an OCR provider."""

    text: str
    warnings: list[str]
    metadata: Mapping[str, Any]


@runtime_checkable
class PDFOCREngine(Protocol):
    """Synchronous OCR adapter contract used by document processing."""

    engine_id: str

    def extract_pdf_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> OCRResult:
        """Return OCR text extracted from a PDF-like document."""


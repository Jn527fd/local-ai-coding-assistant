from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from app.ai.ocr.base import (
    OCREngineExecutionError,
    OCREngineUnavailableError,
    OCRResult,
)


class OCRmyPDFEngine:
    """OCRmyPDF adapter for scanned or image-like PDFs."""

    engine_id = "ocrmypdf"

    def __init__(
        self,
        text_extractor: Callable[[Path], str],
        timeout_seconds: int = 180,
    ) -> None:
        self.text_extractor = text_extractor
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def available() -> bool:
        return shutil.which("ocrmypdf") is not None

    def extract_pdf_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> OCRResult:
        if not self.available():
            raise OCREngineUnavailableError(
                "OCRmyPDF is not installed in the backend runtime."
            )

        language = str(settings.get("language") or "eng").strip() or "eng"
        with tempfile.TemporaryDirectory(prefix="local-ai-ocr-") as temp_dir:
            output_path = Path(temp_dir) / "ocr-output.pdf"
            command = [
                "ocrmypdf",
                "--force-ocr",
                "--language",
                language,
                str(file_path),
                str(output_path),
            ]
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise OCREngineExecutionError("OCRmyPDF timed out.") from exc
            except OSError as exc:
                raise OCREngineExecutionError(
                    f"OCRmyPDF could not be started: {exc}"
                ) from exc

            if completed.returncode != 0:
                message = (completed.stderr or completed.stdout or "").strip()
                raise OCREngineExecutionError(
                    "OCRmyPDF failed to process the PDF"
                    + (f": {message}" if message else ".")
                )

            text = self.text_extractor(output_path)
            warnings = []
            if not text.strip():
                warnings.append("OCRmyPDF completed but produced no extractable text.")
            return OCRResult(
                text=text,
                warnings=warnings,
                metadata={"engine": self.engine_id, "language": language},
            )

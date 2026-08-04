from __future__ import annotations

import importlib
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.ai.ocr.base import (
    OCREngineExecutionError,
    OCREngineUnavailableError,
    OCRResult,
)


class PaddleOCREngine:
    """PaddleOCR adapter for scanned or image-like PDFs."""

    engine_id = "paddleocr"

    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("paddleocr") is not None
            and importlib.util.find_spec("paddle") is not None
            and importlib.util.find_spec("fitz") is not None
        )

    def extract_pdf_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> OCRResult:
        if not self.is_available():
            raise OCREngineUnavailableError(
                "PaddleOCR is not installed in the backend runtime."
            )

        try:
            fitz = importlib.import_module("fitz")
            paddleocr_module = importlib.import_module("paddleocr")
            ocr = self._create_ocr_engine(paddleocr_module, settings)
        except Exception as exc:
            raise OCREngineExecutionError(
                f"PaddleOCR could not be initialized: {exc}"
            ) from exc

        try:
            document = fitz.open(file_path)
            try:
                pages = list(document)
                extracted_pages: list[str] = []
                with tempfile.TemporaryDirectory(prefix="paddleocr-") as tmp:
                    temp_dir = Path(tmp)
                    for page_number, page in enumerate(pages, start=1):
                        image_path = temp_dir / f"page-{page_number}.png"
                        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        pixmap.save(image_path)
                        extracted_pages.append(
                            self._extract_image_text(ocr, image_path)
                        )
            finally:
                document.close()
        except OCREngineExecutionError:
            raise
        except Exception as exc:
            raise OCREngineExecutionError(
                f"PaddleOCR failed to process the PDF: {exc}"
            ) from exc

        text = "\n".join(page for page in extracted_pages if page.strip())
        warnings: list[str] = []
        if not text.strip():
            warnings.append("PaddleOCR completed but produced no extractable text.")
        return OCRResult(
            text=text,
            warnings=warnings,
            metadata={"engine": self.engine_id, "pageCount": len(extracted_pages)},
        )

    def _create_ocr_engine(self, paddleocr_module: Any, settings: Mapping[str, Any]):
        conversation_settings = settings.get("conversationSettings")
        language = "en"
        if isinstance(conversation_settings, Mapping):
            language = str(conversation_settings.get("ocrLanguage") or "en")

        paddle_ocr = paddleocr_module.PaddleOCR
        try:
            return paddle_ocr(use_angle_cls=True, lang=language, show_log=False)
        except TypeError:
            try:
                return paddle_ocr(use_textline_orientation=True, lang=language)
            except TypeError:
                return paddle_ocr(lang=language)

    def _extract_image_text(self, ocr: Any, image_path: Path) -> str:
        try:
            if hasattr(ocr, "ocr"):
                result = ocr.ocr(str(image_path), cls=True)
            elif hasattr(ocr, "predict"):
                result = ocr.predict(str(image_path))
            else:
                raise OCREngineExecutionError(
                    "PaddleOCR object does not expose an OCR method."
                )
        except TypeError:
            result = ocr.ocr(str(image_path))
        except OCREngineExecutionError:
            raise
        except Exception as exc:
            raise OCREngineExecutionError(
                f"PaddleOCR failed to read rendered page image: {exc}"
            ) from exc

        return "\n".join(self._collect_text_values(result))

    def _collect_text_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, Mapping):
            lines: list[str] = []
            for key in ("rec_text", "text", "transcription"):
                if key in value:
                    lines.extend(self._collect_text_values(value[key]))
            for key in ("res", "json", "data", "result"):
                if key in value:
                    lines.extend(self._collect_text_values(value[key]))
            return lines
        if isinstance(value, tuple) and len(value) >= 2:
            second = value[1]
            if isinstance(second, tuple | list) and second:
                return self._collect_text_values(second[0])
        if isinstance(value, list | tuple):
            lines: list[str] = []
            for item in value:
                lines.extend(self._collect_text_values(item))
            return lines

        json_value = getattr(value, "json", None)
        if isinstance(json_value, Mapping):
            return self._collect_text_values(json_value)
        res_value = getattr(value, "res", None)
        if isinstance(res_value, Mapping):
            return self._collect_text_values(res_value)
        return []

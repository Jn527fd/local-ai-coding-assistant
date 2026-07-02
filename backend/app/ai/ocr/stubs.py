from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.ai.components import ComponentNotImplementedError, DocumentText


class UnavailableOCREngine:
    """OCR scaffold that fails explicitly until OCR execution is implemented."""

    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        raise ComponentNotImplementedError(
            "OCR execution is not implemented in this phase."
        )


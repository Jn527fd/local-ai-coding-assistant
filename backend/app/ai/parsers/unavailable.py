from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.ai.components import ComponentNotImplementedError, DocumentText


class UnavailablePDFParser:
    """Explicit placeholder used when a PDF parser adapter has no implementation."""

    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this PDF parser."
        )


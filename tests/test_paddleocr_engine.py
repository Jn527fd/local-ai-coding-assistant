from pathlib import Path
from types import SimpleNamespace

from app.ai.ocr.paddleocr import PaddleOCREngine


class FakePixmap:
    def save(self, path: Path) -> None:
        path.write_bytes(b"fake image")


class FakePage:
    def get_pixmap(self, matrix: object) -> FakePixmap:
        return FakePixmap()


class FakeDocument:
    def __iter__(self):
        return iter([FakePage()])

    def close(self) -> None:
        return None


class FakePaddleOCR:
    def __init__(self, **_kwargs: object) -> None:
        return None

    def ocr(self, _path: str, cls: bool = True) -> list[object]:
        return [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("Scanned text", 0.98)]]


def test_paddleocr_engine_extracts_rendered_pdf_text(monkeypatch, tmp_path: Path) -> None:
    engine = PaddleOCREngine()
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(
        "app.ai.ocr.paddleocr.importlib.import_module",
        lambda name: (
            SimpleNamespace(
                open=lambda _path: FakeDocument(),
                Matrix=lambda _x, _y: object(),
            )
            if name == "fitz"
            else SimpleNamespace(PaddleOCR=FakePaddleOCR)
        ),
    )

    result = engine.extract_pdf_text(pdf_path, settings={})

    assert result.text == "Scanned text"
    assert result.warnings == []
    assert result.metadata == {"engine": "paddleocr", "pageCount": 1}

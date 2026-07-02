from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import re
import uuid
from typing import Any

from app.ai.ocr import (
    OCREngineError,
    OCREngineUnavailableError,
    OCRmyPDFEngine,
    PDFOCREngine,
)
from app.ai.execution_context import AIExecutionContext
from app.schemas.chat import ConversationSettings

ALLOWED_DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf"}
CONVERSATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class DocumentServiceError(Exception):
    """Base error for document staging and processing."""


class DocumentValidationError(DocumentServiceError):
    """Raised when a document request is invalid."""


class DocumentNotFoundError(DocumentServiceError):
    """Raised when a document is absent from the requested conversation."""


class DocumentStorageError(DocumentServiceError):
    """Raised when document artifacts cannot be written safely."""


@dataclass(frozen=True)
class UploadedDocument:
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ProcessedDocument:
    metadata: dict[str, Any]
    extracted: dict[str, Any] | None
    chunks: list[dict[str, Any]]


class DocumentService:
    """Store uploaded conversation documents and derived local artifacts."""

    def __init__(
        self,
        upload_directory: Path,
        max_upload_bytes: int,
        chunk_size: int,
        max_chunks: int = 500,
        ocr_engines: dict[str, PDFOCREngine] | None = None,
    ) -> None:
        self.upload_directory = upload_directory.expanduser().resolve()
        self.max_upload_bytes = max_upload_bytes
        self.chunk_size = chunk_size
        self.max_chunks = max(1, max_chunks)
        self.ocr_engines = (
            self._default_ocr_engines()
            if ocr_engines is None
            else ocr_engines
        )

    def upload(
        self,
        conversation_id: str,
        original_filename: str,
        content_type: str | None,
        content: bytes,
        conversation_settings: ConversationSettings | None = None,
    ) -> UploadedDocument:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        extension = self._extension_from_filename(original_filename)
        if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise DocumentValidationError(
                "Only .txt, .md, and .pdf documents are supported."
            )
        if len(content) > self.max_upload_bytes:
            raise DocumentValidationError(
                "Document is larger than the configured upload limit."
            )

        document_id = uuid.uuid4().hex
        document_directory = self._document_directory(
            safe_conversation_id,
            document_id,
        )
        original_directory = document_directory / "original"
        stored_filename = f"original{extension}"
        stored_path = original_directory / stored_filename

        try:
            original_directory.mkdir(parents=True, exist_ok=False)
            stored_path.write_bytes(content)
        except OSError as exc:
            raise DocumentStorageError(
                "Could not store uploaded document."
            ) from exc

        created_at = self._now()
        metadata = {
            "documentId": document_id,
            "conversationId": safe_conversation_id,
            "originalFilename": self._display_filename(original_filename),
            "storedFilename": stored_filename,
            "storedPath": self._relative_artifact_path(stored_path),
            "mimeType": content_type or "application/octet-stream",
            "size": len(content),
            "extension": extension,
            "createdAt": created_at,
            "processedAt": None,
            "selectedSettings": self._settings_dict(conversation_settings),
            "resolvedParser": None,
            "resolvedOcrEngine": None,
            "selectedChunker": (
                conversation_settings.chunker
                if conversation_settings is not None
                else None
            ),
            "actualChunker": None,
            "extractionWarnings": [],
            "chunkCount": 0,
            "status": "uploaded",
            "error": None,
        }
        self._write_json(document_directory / "metadata.json", metadata)
        return UploadedDocument(metadata=metadata)

    def process(
        self,
        conversation_id: str,
        document_id: str,
        execution_context: AIExecutionContext,
    ) -> ProcessedDocument:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        document_directory = self._existing_document_directory(
            safe_conversation_id,
            document_id,
        )
        metadata = self._read_metadata(
            safe_conversation_id,
            document_id,
            document_directory,
        )
        original_path = self._original_path(document_directory, metadata)
        if original_path is None:
            raise DocumentNotFoundError("Original document artifact was not found.")

        warnings: list[str] = []
        error: str | None = None
        extracted: dict[str, Any] | None = None
        chunks: list[dict[str, Any]] = []
        status = "processed"
        extension = str(metadata.get("extension") or original_path.suffix).lower()

        try:
            text, extraction_warnings = self._extract_text(
                file_path=original_path,
                extension=extension,
                execution_context=execution_context,
            )
            warnings.extend(extraction_warnings)
            if not text.strip():
                raise DocumentValidationError(
                    "No text could be extracted from the document."
                )
            extracted = {
                "documentId": document_id,
                "conversationId": safe_conversation_id,
                "text": text,
                "charLength": len(text),
                "extractedAt": self._now(),
                "extractor": self._extractor_name(extension, execution_context),
                "warnings": warnings,
            }
            chunks, actual_chunker, chunker_warnings = self._chunk_text(
                text=text,
                document_id=document_id,
                conversation_id=safe_conversation_id,
                selected_chunker=execution_context.conversation_settings.chunker,
                extension=extension,
            )
            warnings.extend(chunker_warnings)
            metadata["actualChunker"] = actual_chunker
        except DocumentServiceError as exc:
            status = "failed"
            error = str(exc)
        except (OSError, UnicodeError, ValueError) as exc:
            status = "failed"
            error = f"Document processing failed: {exc}"

        processed_at = self._now()
        metadata.update(
            {
                "processedAt": processed_at,
                "selectedSettings": self._settings_dict(
                    execution_context.conversation_settings
                ),
                "resolvedParser": execution_context.resolved_pdf_parser,
                "resolvedOcrEngine": execution_context.resolved_ocr_engine,
                "selectedChunker": (
                    execution_context.conversation_settings.chunker
                ),
                "extractionWarnings": warnings,
                "chunkCount": len(chunks),
                "status": status,
                "error": error,
            }
        )
        if status == "failed" and metadata.get("actualChunker") is None:
            metadata["actualChunker"] = None

        if extracted is not None:
            self._write_json(document_directory / "extracted.json", extracted)
        self._write_json(
            document_directory / "chunks.json",
            {
                "documentId": document_id,
                "conversationId": safe_conversation_id,
                "chunks": chunks,
            },
        )
        self._write_json(document_directory / "metadata.json", metadata)
        return ProcessedDocument(
            metadata=metadata,
            extracted=extracted,
            chunks=chunks,
        )

    def list_documents(self, conversation_id: str) -> list[dict[str, Any]]:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        conversation_directory = self._conversation_directory(
            safe_conversation_id
        )
        if not conversation_directory.exists():
            return []

        documents: list[dict[str, Any]] = []
        for document_directory in sorted(conversation_directory.iterdir()):
            if not document_directory.is_dir():
                continue
            documents.append(
                self._read_metadata(
                    safe_conversation_id,
                    document_directory.name,
                    document_directory,
                )
            )
        documents.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        return documents

    def get_document(
        self,
        conversation_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        document_directory = self._existing_document_directory(
            safe_conversation_id,
            document_id,
        )
        return self._read_metadata(
            safe_conversation_id,
            document_id,
            document_directory,
        )

    def get_chunks(
        self,
        conversation_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        document_directory = self._existing_document_directory(
            safe_conversation_id,
            document_id,
        )
        metadata = self._read_metadata(
            safe_conversation_id,
            document_id,
            document_directory,
        )
        chunks_path = document_directory / "chunks.json"
        if not chunks_path.exists():
            return {
                "documentId": document_id,
                "conversationId": safe_conversation_id,
                "status": metadata.get("status", "uploaded"),
                "chunks": [],
                "warning": "Chunks artifact is not available.",
            }
        try:
            data = self._read_json(chunks_path)
        except DocumentStorageError as exc:
            return {
                "documentId": document_id,
                "conversationId": safe_conversation_id,
                "status": "failed",
                "chunks": [],
                "warning": str(exc),
            }
        chunks = data.get("chunks") if isinstance(data, dict) else None
        if not isinstance(chunks, list):
            return {
                "documentId": document_id,
                "conversationId": safe_conversation_id,
                "status": metadata.get("status", "uploaded"),
                "chunks": [],
                "warning": "Chunks artifact is invalid.",
            }
        return {
            "documentId": document_id,
            "conversationId": safe_conversation_id,
            "status": metadata.get("status", "uploaded"),
            "chunks": chunks,
        }

    def _extract_text(
        self,
        file_path: Path,
        extension: str,
        execution_context: AIExecutionContext,
    ) -> tuple[str, list[str]]:
        if extension in {".txt", ".md"}:
            return self._extract_plain_text(file_path)
        if extension == ".pdf":
            return self._extract_pdf_text(file_path, execution_context)
        raise DocumentValidationError("Unsupported document type.")

    def _extract_plain_text(self, file_path: Path) -> tuple[str, list[str]]:
        content = file_path.read_bytes()
        try:
            return content.decode("utf-8"), []
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace"), [
                "Document was decoded as UTF-8 with replacement characters.",
            ]

    def _extract_pdf_text(
        self,
        file_path: Path,
        execution_context: AIExecutionContext,
    ) -> tuple[str, list[str]]:
        warnings: list[str] = []
        parser = execution_context.resolved_pdf_parser
        if parser in {"", "none"}:
            raise DocumentValidationError(
                "No available PDF parser is configured for this document."
            )

        if parser == "pymupdf":
            text = self._extract_with_pymupdf(file_path)
        elif parser == "pdfplumber":
            text = self._extract_with_pdfplumber(file_path)
        elif parser == "docling":
            raise DocumentValidationError(
                "Docling is discoverable but no PDF extraction adapter is "
                "registered yet."
            )
        else:
            raise DocumentValidationError(
                f"PDF parser '{parser}' is not supported by the document service."
            )

        if len(text.strip()) < 20 and execution_context.resolved_ocr_engine != "none":
            try:
                ocr_text, ocr_warnings = self._run_ocr(file_path, execution_context)
                warnings.extend(ocr_warnings)
                if ocr_text.strip():
                    text = ocr_text
            except (OCREngineError, DocumentServiceError) as exc:
                warnings.append(str(exc))

        if not text.strip():
            raise DocumentValidationError("No text could be extracted from the PDF.")
        return text, warnings

    def _extract_with_pymupdf(self, file_path: Path) -> str:
        try:
            fitz = importlib.import_module("fitz")
        except ImportError as exc:
            raise DocumentValidationError("PyMuPDF is not installed.") from exc

        try:
            document = fitz.open(file_path)
            try:
                return "\n".join(page.get_text() for page in document)
            finally:
                document.close()
        except Exception as exc:
            raise DocumentValidationError(
                f"PyMuPDF could not extract text: {exc}"
            ) from exc

    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        try:
            pdfplumber = importlib.import_module("pdfplumber")
        except ImportError as exc:
            raise DocumentValidationError("pdfplumber is not installed.") from exc

        try:
            with pdfplumber.open(file_path) as document:
                return "\n".join(
                    page.extract_text() or ""
                    for page in document.pages
                )
        except Exception as exc:
            raise DocumentValidationError(
                f"pdfplumber could not extract text: {exc}"
            ) from exc

    def _run_ocr(
        self,
        file_path: Path,
        execution_context: AIExecutionContext,
    ) -> tuple[str, list[str]]:
        engine_id = execution_context.resolved_ocr_engine
        if engine_id == "none":
            return "", []

        engine = self.ocr_engines.get(engine_id)
        if engine is None:
            raise OCREngineUnavailableError(
                f"OCR engine '{engine_id}' is not available for PDF OCR execution."
            )

        result = engine.extract_pdf_text(
            file_path=file_path,
            settings={
                "conversationSettings": execution_context.conversation_settings.model_dump(),
            },
        )
        warnings = [
            f"OCR fallback used '{engine_id}' because selectable PDF text was limited.",
            *result.warnings,
        ]
        return result.text, warnings

    def _chunk_text(
        self,
        text: str,
        document_id: str,
        conversation_id: str,
        selected_chunker: str | None,
        extension: str,
    ) -> tuple[list[dict[str, Any]], str, list[str]]:
        chunker = (selected_chunker or "recursive").strip() or "recursive"
        warnings: list[str] = []
        actual_chunker = chunker
        if chunker in {"semantic", "document-aware"}:
            actual_chunker = "recursive"
            warnings.append(
                f"Chunker '{chunker}' is not implemented yet; used recursive."
            )
        elif chunker not in {"fixed", "recursive"}:
            actual_chunker = "recursive"
            warnings.append(
                f"Chunker '{chunker}' is not supported; used recursive."
            )

        spans = (
            self._fixed_spans(text)
            if actual_chunker == "fixed"
            else self._recursive_spans(text)
        )
        chunks: list[dict[str, Any]] = []
        if len(spans) > self.max_chunks:
            spans = spans[: self.max_chunks]
            warnings.append(
                "Document produced more chunks than the configured limit; "
                f"kept the first {self.max_chunks} chunks."
            )

        for index, (start, end) in enumerate(spans):
            chunk_text = text[start:end]
            chunks.append(
                {
                    "chunkId": f"{document_id}:{index}",
                    "documentId": document_id,
                    "conversationId": conversation_id,
                    "index": index,
                    "text": chunk_text,
                    "charStart": start,
                    "charEnd": end,
                    "charLength": len(chunk_text),
                    "tokenEstimate": max(1, (len(chunk_text) + 3) // 4),
                    "metadata": {
                        "chunker": actual_chunker,
                        "selectedChunker": chunker,
                        "extension": extension,
                    },
                }
            )
        return chunks, actual_chunker, warnings

    def _fixed_spans(self, text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for start in range(0, len(text), self.chunk_size):
            end = min(len(text), start + self.chunk_size)
            if text[start:end].strip():
                spans.append((start, end))
        return spans

    def _recursive_spans(self, text: str) -> list[tuple[int, int]]:
        blocks = [
            (match.start(), match.end())
            for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text)
        ]
        if not blocks:
            return []

        spans: list[tuple[int, int]] = []
        current_start: int | None = None
        current_end: int | None = None

        for start, end in blocks:
            if end - start > self.chunk_size:
                if current_start is not None and current_end is not None:
                    spans.append((current_start, current_end))
                    current_start = None
                    current_end = None
                spans.extend(self._split_large_span(text, start, end))
                continue

            if current_start is None:
                current_start = start
                current_end = end
                continue

            if end - current_start <= self.chunk_size:
                current_end = end
                continue

            spans.append((current_start, current_end or end))
            current_start = start
            current_end = end

        if current_start is not None and current_end is not None:
            spans.append((current_start, current_end))
        return spans

    def _split_large_span(
        self,
        text: str,
        start: int,
        end: int,
    ) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        cursor = start
        while cursor < end:
            next_end = min(end, cursor + self.chunk_size)
            if next_end < end:
                boundary = text.rfind("\n", cursor, next_end)
                if boundary <= cursor:
                    boundary = text.rfind(". ", cursor, next_end)
                if boundary > cursor:
                    next_end = boundary + 1
            if text[cursor:next_end].strip():
                spans.append((cursor, next_end))
            cursor = max(next_end, cursor + 1)
        return spans

    def _read_metadata(
        self,
        conversation_id: str,
        document_id: str,
        document_directory: Path,
    ) -> dict[str, Any]:
        metadata_path = document_directory / "metadata.json"
        if not metadata_path.exists():
            return self._fallback_metadata(
                conversation_id,
                document_id,
                "Metadata artifact is missing.",
            )
        try:
            data = self._read_json(metadata_path)
        except DocumentStorageError as exc:
            return self._fallback_metadata(conversation_id, document_id, str(exc))
        if not isinstance(data, dict):
            return self._fallback_metadata(
                conversation_id,
                document_id,
                "Metadata artifact is invalid.",
            )
        stored_document_id = data.get("documentId")
        stored_conversation_id = data.get("conversationId")
        if stored_document_id not in {None, document_id}:
            return self._fallback_metadata(
                conversation_id,
                document_id,
                "Metadata artifact documentId does not match its storage path.",
            )
        if stored_conversation_id not in {None, conversation_id}:
            return self._fallback_metadata(
                conversation_id,
                document_id,
                "Metadata artifact conversationId does not match its storage path.",
            )
        data.setdefault("documentId", document_id)
        data.setdefault("conversationId", conversation_id)
        return data

    def _default_ocr_engines(self) -> dict[str, PDFOCREngine]:
        return {
            "ocrmypdf": OCRmyPDFEngine(
                text_extractor=self._extract_with_pymupdf,
            )
        }

    def _fallback_metadata(
        self,
        conversation_id: str,
        document_id: str,
        warning: str,
    ) -> dict[str, Any]:
        return {
            "documentId": document_id,
            "conversationId": conversation_id,
            "originalFilename": "Unknown document",
            "storedFilename": None,
            "storedPath": None,
            "mimeType": None,
            "size": None,
            "extension": None,
            "createdAt": None,
            "processedAt": None,
            "selectedSettings": {},
            "resolvedParser": None,
            "resolvedOcrEngine": None,
            "selectedChunker": None,
            "actualChunker": None,
            "extractionWarnings": [warning],
            "chunkCount": 0,
            "status": "failed",
            "error": warning,
        }

    def _original_path(
        self,
        document_directory: Path,
        metadata: dict[str, Any],
    ) -> Path | None:
        stored_filename = metadata.get("storedFilename")
        if not isinstance(stored_filename, str):
            return None
        original_path = (document_directory / "original" / stored_filename).resolve()
        self._ensure_within(document_directory, original_path)
        return original_path if original_path.exists() else None

    def _existing_document_directory(
        self,
        conversation_id: str,
        document_id: str,
    ) -> Path:
        if not re.fullmatch(r"^[a-f0-9]{32}$", document_id):
            raise DocumentNotFoundError("Document was not found.")
        document_directory = self._document_directory(conversation_id, document_id)
        if not document_directory.exists() or not document_directory.is_dir():
            raise DocumentNotFoundError("Document was not found.")
        return document_directory

    def _document_directory(
        self,
        conversation_id: str,
        document_id: str,
    ) -> Path:
        document_directory = (
            self._conversation_directory(conversation_id) / document_id
        ).resolve()
        self._ensure_within(self.upload_directory, document_directory)
        return document_directory

    def _conversation_directory(self, conversation_id: str) -> Path:
        conversation_directory = (self.upload_directory / conversation_id).resolve()
        self._ensure_within(self.upload_directory, conversation_directory)
        return conversation_directory

    def _validate_conversation_id(self, conversation_id: str) -> str:
        if not CONVERSATION_ID_PATTERN.fullmatch(conversation_id):
            raise DocumentValidationError("Invalid conversationId.")
        if conversation_id in {".", ".."}:
            raise DocumentValidationError("Invalid conversationId.")
        return conversation_id

    def _extension_from_filename(self, filename: str) -> str:
        name = self._display_filename(filename)
        return Path(name).suffix.lower()

    @staticmethod
    def _display_filename(filename: str) -> str:
        name = Path(filename or "document").name
        cleaned = re.sub(r"[\x00-\x1f\x7f]+", "", name).strip()
        return cleaned or "document"

    def _relative_artifact_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.upload_directory).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def _settings_dict(
        conversation_settings: ConversationSettings | None,
    ) -> dict[str, Any]:
        if conversation_settings is None:
            return {}
        return conversation_settings.model_dump()

    @staticmethod
    def _extractor_name(
        extension: str,
        execution_context: AIExecutionContext,
    ) -> str:
        if extension in {".txt", ".md"}:
            return "plain-text"
        if extension == ".pdf":
            return execution_context.resolved_pdf_parser
        return "unknown"

    def _read_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DocumentStorageError(
                f"Could not read artifact {path.name}."
            ) from exc

    def _write_json(self, path: Path, data: Any) -> None:
        self._ensure_within(self.upload_directory, path.resolve())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise DocumentStorageError(
                f"Could not write artifact {path.name}."
            ) from exc

    @staticmethod
    def _ensure_within(root: Path, path: Path) -> None:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise DocumentValidationError("Invalid document path.") from exc

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

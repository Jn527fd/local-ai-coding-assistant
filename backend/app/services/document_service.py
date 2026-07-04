from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import io
import importlib
import json
from pathlib import Path
import re
import uuid
from typing import Any
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from app.ai.ocr import (
    OCREngineError,
    OCREngineUnavailableError,
    OCRmyPDFEngine,
    PDFOCREngine,
)
from app.ai.execution_context import AIExecutionContext
from app.schemas.chat import ConversationSettings

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".html",
    ".htm",
    ".csv",
    ".tsv",
}
CONVERSATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


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


@dataclass(frozen=True)
class SniffedDocumentType:
    extension: str
    content_type: str
    confidence: str
    warnings: list[str]


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
        filename_extension = self._extension_from_filename(original_filename)
        if filename_extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise DocumentValidationError(
                "Only .txt, .md, .pdf, .docx, .html, .csv, and .tsv documents "
                "are supported."
            )
        if len(content) > self.max_upload_bytes:
            raise DocumentValidationError(
                "Document is larger than the configured upload limit."
            )
        sniffed = self._sniff_document_type(
            filename_extension,
            content_type,
            content,
        )
        content_hash = hashlib.sha256(content).hexdigest()
        duplicate = self._find_duplicate(
            safe_conversation_id,
            content_hash,
        )

        document_id = str(duplicate.get("documentId")) if duplicate else uuid.uuid4().hex
        document_directory = self._document_directory(
            safe_conversation_id,
            document_id,
        )
        original_directory = document_directory / "original"
        stored_filename = f"original{sniffed.extension}"
        stored_path = original_directory / stored_filename

        if not duplicate:
            try:
                original_directory.mkdir(parents=True, exist_ok=False)
                stored_path.write_bytes(content)
            except OSError as exc:
                raise DocumentStorageError(
                    "Could not store uploaded document."
                ) from exc

        created_at = self._now()
        existing_warnings = (
            duplicate.get("extractionWarnings", [])
            if isinstance(duplicate, dict)
            else []
        )
        metadata = {
            "documentId": document_id,
            "conversationId": safe_conversation_id,
            "originalFilename": self._display_filename(original_filename),
            "storedFilename": stored_filename,
            "storedPath": self._relative_artifact_path(stored_path),
            "mimeType": sniffed.content_type,
            "size": len(content),
            "contentHash": content_hash,
            "extension": sniffed.extension,
            "detectedType": sniffed.extension.strip("."),
            "sniffConfidence": sniffed.confidence,
            "createdAt": duplicate.get("createdAt") if duplicate else created_at,
            "processedAt": duplicate.get("processedAt") if duplicate else None,
            "selectedSettings": self._settings_dict(conversation_settings),
            "resolvedParser": duplicate.get("resolvedParser") if duplicate else None,
            "resolvedOcrEngine": duplicate.get("resolvedOcrEngine") if duplicate else None,
            "selectedChunker": (
                conversation_settings.chunker
                if conversation_settings is not None
                else None
            ),
            "actualChunker": duplicate.get("actualChunker") if duplicate else None,
            "extractionWarnings": [
                *(
                    warning
                    for warning in existing_warnings
                    if isinstance(warning, str)
                ),
                *sniffed.warnings,
            ],
            "chunkCount": duplicate.get("chunkCount", 0) if duplicate else 0,
            "status": duplicate.get("status", "uploaded") if duplicate else "uploaded",
            "error": duplicate.get("error") if duplicate else None,
            "duplicateOf": duplicate.get("documentId") if duplicate else None,
            "duplicate": duplicate is not None,
            "extractionDiagnostics": (
                duplicate.get("extractionDiagnostics", {})
                if duplicate
                else {
                    "detectedType": sniffed.extension.strip("."),
                    "sniffConfidence": sniffed.confidence,
                    "mimeType": sniffed.content_type,
                    "sizeBytes": len(content),
                    "contentHash": content_hash,
                }
            ),
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
            text, extraction_warnings, diagnostics = self._extract_text(
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
                "diagnostics": diagnostics,
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
                "extractionDiagnostics": {
                    **metadata.get("extractionDiagnostics", {}),
                    **(extracted.get("diagnostics", {}) if extracted else {}),
                    "charLength": len(extracted["text"]) if extracted else 0,
                    "chunkCount": len(chunks),
                },
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
    ) -> tuple[str, list[str], dict[str, Any]]:
        if extension in {".txt", ".md"}:
            return self._extract_plain_text(file_path)
        if extension == ".pdf":
            return self._extract_pdf_text(file_path, execution_context)
        if extension == ".docx":
            return self._extract_docx_text(file_path)
        if extension in {".html", ".htm"}:
            return self._extract_html_text(file_path)
        if extension in {".csv", ".tsv"}:
            return self._extract_delimited_text(file_path, extension)
        raise DocumentValidationError("Unsupported document type.")

    def _extract_plain_text(self, file_path: Path) -> tuple[str, list[str], dict[str, Any]]:
        content = file_path.read_bytes()
        try:
            text = content.decode("utf-8")
            return text, [], self._text_diagnostics(text, "plain-text")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
            return text, [
                "Document was decoded as UTF-8 with replacement characters.",
            ], self._text_diagnostics(text, "plain-text")

    def _extract_pdf_text(
        self,
        file_path: Path,
        execution_context: AIExecutionContext,
    ) -> tuple[str, list[str], dict[str, Any]]:
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
        return text, warnings, self._text_diagnostics(text, "pdf")

    def _extract_docx_text(self, file_path: Path) -> tuple[str, list[str], dict[str, Any]]:
        try:
            with ZipFile(file_path) as archive:
                try:
                    xml_bytes = archive.read("word/document.xml")
                except KeyError as exc:
                    raise DocumentValidationError(
                        "DOCX file is missing word/document.xml."
                    ) from exc
        except BadZipFile as exc:
            raise DocumentValidationError("DOCX file is not a valid ZIP container.") from exc
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            raise DocumentValidationError("DOCX document XML is malformed.") from exc
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs: list[str] = []
        for paragraph in root.iter(f"{namespace}p"):
            texts = [
                node.text or ""
                for node in paragraph.iter(f"{namespace}t")
                if node.text
            ]
            if texts:
                paragraphs.append("".join(texts))
        text = "\n".join(paragraphs)
        diagnostics = self._text_diagnostics(text, "docx")
        diagnostics["paragraphCount"] = len(paragraphs)
        return text, [], diagnostics

    def _extract_html_text(self, file_path: Path) -> tuple[str, list[str], dict[str, Any]]:
        raw = file_path.read_bytes()
        try:
            html = raw.decode("utf-8")
            warnings: list[str] = []
        except UnicodeDecodeError:
            html = raw.decode("utf-8", errors="replace")
            warnings = ["HTML document was decoded as UTF-8 with replacement characters."]
        parser = _HTMLTextExtractor()
        parser.feed(html)
        text = parser.text()
        diagnostics = self._text_diagnostics(text, "html")
        diagnostics["elementCount"] = parser.element_count
        return text, warnings, diagnostics

    def _extract_delimited_text(
        self,
        file_path: Path,
        extension: str,
    ) -> tuple[str, list[str], dict[str, Any]]:
        raw = file_path.read_bytes()
        try:
            content = raw.decode("utf-8-sig")
            warnings: list[str] = []
        except UnicodeDecodeError:
            content = raw.decode("utf-8-sig", errors="replace")
            warnings = ["Delimited document was decoded as UTF-8 with replacement characters."]
        delimiter = "\t" if extension == ".tsv" else ","
        try:
            rows = list(csv.reader(content.splitlines(), delimiter=delimiter))
        except csv.Error as exc:
            raise DocumentValidationError(f"Delimited document is malformed: {exc}") from exc
        lines = [
            " | ".join(str(cell).strip() for cell in row)
            for row in rows
            if any(str(cell).strip() for cell in row)
        ]
        text = "\n".join(lines)
        diagnostics = self._text_diagnostics(text, extension.strip("."))
        diagnostics["rowCount"] = len(rows)
        diagnostics["columnCount"] = max((len(row) for row in rows), default=0)
        return text, warnings, diagnostics

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
            "extractionDiagnostics": {},
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

    def _sniff_document_type(
        self,
        extension: str,
        content_type: str | None,
        content: bytes,
    ) -> SniffedDocumentType:
        warnings: list[str] = []
        mime_type = content_type or "application/octet-stream"
        normalized_mime = mime_type.split(";", maxsplit=1)[0].strip().lower()
        signature_extension = self._signature_extension(content)
        text_like = self._looks_like_text(content)

        if extension == ".pdf" and signature_extension != ".pdf":
            raise DocumentValidationError("PDF upload is malformed or has the wrong file type.")
        if extension == ".docx" and signature_extension != ".docx":
            raise DocumentValidationError("DOCX upload is malformed or has the wrong file type.")
        if extension in {".txt", ".md", ".html", ".htm", ".csv", ".tsv"} and not text_like:
            raise DocumentValidationError(
                "Text-like document upload is malformed or has the wrong file type."
            )
        if signature_extension in {".pdf", ".docx"} and signature_extension != extension:
            raise DocumentValidationError(
                "Uploaded file content does not match the filename extension."
            )

        expected_mimes = {
            ".txt": {"text/plain", "application/octet-stream"},
            ".md": {"text/markdown", "text/plain", "application/octet-stream"},
            ".pdf": {"application/pdf", "application/octet-stream"},
            ".docx": {DOCX_CONTENT_TYPE, "application/octet-stream"},
            ".html": {"text/html", "application/xhtml+xml", "text/plain", "application/octet-stream"},
            ".htm": {"text/html", "application/xhtml+xml", "text/plain", "application/octet-stream"},
            ".csv": {"text/csv", "application/csv", "text/plain", "application/octet-stream"},
            ".tsv": {"text/tab-separated-values", "text/plain", "application/octet-stream"},
        }
        if normalized_mime and normalized_mime not in expected_mimes.get(extension, set()):
            warnings.append(
                f"Upload MIME type '{normalized_mime}' did not match extension '{extension}'."
            )

        return SniffedDocumentType(
            extension=extension,
            content_type=normalized_mime or "application/octet-stream",
            confidence="signature" if signature_extension else "text",
            warnings=warnings,
        )

    @staticmethod
    def _signature_extension(content: bytes) -> str | None:
        if content.startswith(b"%PDF-"):
            return ".pdf"
        if content.startswith(b"PK\x03\x04"):
            try:
                with ZipFile(io.BytesIO(content)) as archive:
                    names = set(archive.namelist())
            except BadZipFile:
                return ".zip"
            if "word/document.xml" in names:
                return ".docx"
            return ".zip"
        return None

    @staticmethod
    def _looks_like_text(content: bytes) -> bool:
        return b"\x00" not in content[:4096]

    def _find_duplicate(
        self,
        conversation_id: str,
        content_hash: str,
    ) -> dict[str, Any] | None:
        conversation_directory = self._conversation_directory(conversation_id)
        if not conversation_directory.exists():
            return None
        for document_directory in sorted(conversation_directory.iterdir()):
            if not document_directory.is_dir():
                continue
            metadata = self._read_metadata(
                conversation_id,
                document_directory.name,
                document_directory,
            )
            if metadata.get("contentHash") == content_hash:
                return metadata
        return None

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
        if extension == ".docx":
            return "docx-zip-xml"
        if extension in {".html", ".htm"}:
            return "html-parser"
        if extension in {".csv", ".tsv"}:
            return "csv"
        return "unknown"

    @staticmethod
    def _text_diagnostics(text: str, extractor: str) -> dict[str, Any]:
        lines = text.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]
        return {
            "extractor": extractor,
            "charLength": len(text),
            "lineCount": len(lines),
            "nonEmptyLineCount": len(non_empty_lines),
            "wordEstimate": len(re.findall(r"\S+", text)),
        }

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


class _HTMLTextExtractor(HTMLParser):
    """Small stdlib HTML-to-text extractor for trusted local documents."""

    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "section",
        "table",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.element_count = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.element_count += 1
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        joined = " ".join(self.parts)
        lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in joined.splitlines()
        ]
        return "\n".join(line for line in lines if line)

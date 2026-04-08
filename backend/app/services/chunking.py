from dataclasses import dataclass
import re
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import get_settings
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.schemas.documents import (
    DocumentChunkResponse,
    DocumentChunkingResponse,
)
from backend.app.services.document_service import DocumentNotFoundError
from backend.app.services.text_extraction import extract_document_text

settings = get_settings()

PAGE_MARKER_PATTERN = re.compile(r"^\[Page (\d+)\]$")


@dataclass
class ChunkCandidate:
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_reference: int | list[int] | None
    overlap_from_previous_chars: int


def chunk_document(
    db: Session, document_id: int, tenant_id: int | None = None
) -> DocumentChunkingResponse:
    document = _get_document_model(db, document_id, tenant_id)
    extraction = extract_document_text(
        db,
        document_id,
        tenant_id if tenant_id is not None else document.collection.tenant_id,
    )
    cleaned_text, page_spans = _strip_page_markers(extraction.extracted_text)
    candidates = _build_chunk_candidates(cleaned_text, page_spans)

    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

    chunk_rows: list[DocumentChunk] = []
    response_chunks: list[DocumentChunkResponse] = []
    for candidate in candidates:
        metadata_json = {
            "page_reference": candidate.page_reference,
            "start_char": candidate.start_char,
            "end_char": candidate.end_char,
            "overlap_from_previous_chars": candidate.overlap_from_previous_chars,
        }
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=candidate.chunk_index,
            text=candidate.text,
            metadata_json=metadata_json,
        )
        db.add(chunk)
        chunk_rows.append(chunk)
        response_chunks.append(
            DocumentChunkResponse(
                chunk_index=candidate.chunk_index,
                text=candidate.text,
                metadata_json=metadata_json,
            )
        )

    db.commit()

    return DocumentChunkingResponse(
        document_id=document.id,
        filename=document.filename,
        chunk_count=len(response_chunks),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_min_length=settings.chunk_min_length,
        chunks=response_chunks,
    )


def _build_chunk_candidates(
    text: str, page_spans: list[tuple[int, int, int]]
) -> list[ChunkCandidate]:
    normalized_text, normalized_page_spans = _trim_text_and_spans(text, page_spans)
    if not normalized_text:
        return []

    candidates: list[ChunkCandidate] = []
    start = 0
    text_length = len(normalized_text)
    chunk_index = 0
    previous_end = 0

    while start < text_length:
        tentative_end = min(start + settings.chunk_size, text_length)
        end = _choose_chunk_end(normalized_text, start, tentative_end)

        chunk_text = normalized_text[start:end].strip()
        if not chunk_text:
            start = end + 1
            continue

        actual_start = normalized_text.find(chunk_text, start, end + 1)
        actual_end = actual_start + len(chunk_text)
        page_reference = _resolve_page_reference(
            normalized_page_spans, actual_start, actual_end
        )
        overlap = max(0, previous_end - actual_start) if chunk_index > 0 else 0

        candidates.append(
            ChunkCandidate(
                chunk_index=chunk_index,
                text=chunk_text,
                start_char=actual_start,
                end_char=actual_end,
                page_reference=page_reference,
                overlap_from_previous_chars=overlap,
            )
        )

        if actual_end >= text_length:
            break

        previous_end = actual_end
        next_start = max(actual_end - settings.chunk_overlap, actual_start + 1)
        start = _normalize_chunk_start(normalized_text, next_start)
        chunk_index += 1

    return candidates


def _choose_chunk_end(text: str, start: int, tentative_end: int) -> int:
    if tentative_end >= len(text):
        return len(text)

    preferred_breaks = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
    search_start = min(start + settings.chunk_min_length, tentative_end)

    for marker in preferred_breaks:
        index = text.rfind(marker, search_start, tentative_end)
        if index != -1:
            if marker.isspace():
                return index
            return index + len(marker.rstrip())

    return tentative_end


def _normalize_chunk_start(text: str, start: int) -> int:
    if 0 < start < len(text) and not text[start].isspace() and not text[start - 1].isspace():
        while start < len(text) and not text[start].isspace():
            start += 1
    while start < len(text) and text[start].isspace():
        start += 1
    return start


def _strip_page_markers(text: str) -> tuple[str, list[tuple[int, int, int]]]:
    if not text:
        return "", []

    lines = text.splitlines()
    current_page: int | None = None
    output_parts: list[str] = []
    page_spans: list[tuple[int, int, int]] = []
    cursor = 0

    for line in lines:
        marker_match = PAGE_MARKER_PATTERN.match(line.strip())
        if marker_match:
            current_page = int(marker_match.group(1))
            continue

        content = line
        if output_parts:
            output_parts.append("\n")
            cursor += 1

        if content:
            start = cursor
            output_parts.append(content)
            cursor += len(content)
            if current_page is not None:
                page_spans.append((start, cursor, current_page))

    return "".join(output_parts), _merge_page_spans(page_spans)


def _merge_page_spans(
    spans: list[tuple[int, int, int]]
) -> list[tuple[int, int, int]]:
    if not spans:
        return []

    merged: list[tuple[int, int, int]] = [spans[0]]
    for start, end, page in spans[1:]:
        prev_start, prev_end, prev_page = merged[-1]
        if prev_page == page and start <= prev_end + 1:
            merged[-1] = (prev_start, end, prev_page)
        else:
            merged.append((start, end, page))
    return merged


def _trim_text_and_spans(
    text: str, page_spans: list[tuple[int, int, int]]
) -> tuple[str, list[tuple[int, int, int]]]:
    if not text:
        return "", []

    leading_trim = len(text) - len(text.lstrip())
    trailing_trim = len(text.rstrip())
    trimmed_text = text.strip()
    if not trimmed_text:
        return "", []

    trimmed_spans: list[tuple[int, int, int]] = []
    for start, end, page in page_spans:
        adjusted_start = max(start - leading_trim, 0)
        adjusted_end = max(end - leading_trim, 0)
        adjusted_start = min(adjusted_start, len(trimmed_text))
        adjusted_end = min(adjusted_end, len(trimmed_text))
        if adjusted_end > adjusted_start and start < trailing_trim:
            trimmed_spans.append((adjusted_start, adjusted_end, page))

    return trimmed_text, trimmed_spans


def _resolve_page_reference(
    page_spans: list[tuple[int, int, int]], start: int, end: int
) -> int | list[int] | None:
    pages = [
        page
        for span_start, span_end, page in page_spans
        if span_start < end and span_end > start
    ]
    unique_pages = sorted(set(pages))
    if not unique_pages:
        return None
    if len(unique_pages) == 1:
        return unique_pages[0]
    return unique_pages


def _get_document_model(
    db: Session, document_id: int, tenant_id: int | None = None
) -> Document:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.collection), selectinload(Document.chunks))
    )
    if tenant_id is not None:
        statement = statement.join(Document.collection).where(
            Document.collection.has(tenant_id=tenant_id)
        )
    document = db.scalar(statement)
    if document is None:
        raise DocumentNotFoundError
    return document

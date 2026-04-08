from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.document import Document
from backend.app.schemas.documents import DocumentExtractionResponse
from backend.app.services.document_parsers import (
    DocxDocumentParser,
    DocumentParser,
    PdfDocumentParser,
    TxtDocumentParser,
)
from backend.app.services.document_service import DocumentNotFoundError
from backend.app.services.storage import LocalFileStorage

PARSERS_BY_SOURCE_TYPE: dict[str, DocumentParser] = {
    "txt": TxtDocumentParser(),
    "pdf": PdfDocumentParser(),
    "docx": DocxDocumentParser(),
}


class DocumentExtractionNotAvailableError(Exception):
    """Raised when extraction cannot proceed for the requested document."""


def extract_document_text(
    db: Session, document_id: int, tenant_id: int
) -> DocumentExtractionResponse:
    document = _get_document_model(db, document_id, tenant_id)
    parser = PARSERS_BY_SOURCE_TYPE.get(document.source_type)
    if parser is None:
        raise DocumentExtractionNotAvailableError(
            f"No parser is configured for source type '{document.source_type}'."
        )

    storage_path = document.metadata_json.get("storage_path")
    if not storage_path:
        raise DocumentExtractionNotAvailableError(
            "Document does not have a stored file path."
        )

    storage = LocalFileStorage()
    file_path = storage.resolve_path(storage_path)
    if not file_path.exists():
        raise DocumentExtractionNotAvailableError(
            f"Stored file does not exist at '{storage_path}'."
        )

    extraction = parser.parse(file_path)
    parser_metadata = dict(extraction.parser_metadata)
    parser_metadata["storage_path"] = storage_path

    return DocumentExtractionResponse(
        document_id=document.id,
        filename=document.filename,
        source_type=document.source_type,
        extracted_text=extraction.extracted_text,
        parser_metadata=parser_metadata,
    )


def _get_document_model(db: Session, document_id: int, tenant_id: int) -> Document:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .join(Document.collection)
        .where(Document.collection.has(tenant_id=tenant_id))
        .options(selectinload(Document.collection), selectinload(Document.chunks))
    )
    document = db.scalar(statement)
    if document is None:
        raise DocumentNotFoundError
    return document

from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from backend.app.models.document import Document
from backend.app.schemas.documents import (
    DocumentCollectionInfo,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentUploadResponse,
)
from backend.app.services.collection_service import get_collection
from backend.app.services.storage import LocalFileStorage

SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": {"source_type": "pdf", "content_types": {"application/pdf"}},
    ".docx": {
        "source_type": "docx",
        "content_types": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
    },
    ".txt": {"source_type": "txt", "content_types": {"text/plain"}},
}


class UnsupportedDocumentTypeError(Exception):
    """Raised when an uploaded file type is not supported."""


class DocumentNotFoundError(Exception):
    """Raised when the requested document does not exist."""


def upload_document(
    db: Session, collection_id: int, file: UploadFile
) -> DocumentUploadResponse:
    get_collection(db, collection_id)

    extension = Path(file.filename or "").suffix.lower()
    document_type = SUPPORTED_DOCUMENT_TYPES.get(extension)
    if document_type is None:
        raise UnsupportedDocumentTypeError(
            "Unsupported document type. Only PDF, DOCX, and TXT uploads are allowed."
        )

    content_type = file.content_type or "application/octet-stream"
    allowed_content_types = document_type["content_types"]
    if content_type not in allowed_content_types and content_type != "application/octet-stream":
        raise UnsupportedDocumentTypeError(
            f"Unsupported content type '{content_type}' for {extension} uploads."
        )

    storage = LocalFileStorage()
    stored_file = storage.save_upload(file=file, collection_id=collection_id)

    document = Document(
        collection_id=collection_id,
        filename=stored_file.original_filename,
        source_type=document_type["source_type"],
        status="uploaded",
        metadata_json={
            "original_filename": stored_file.original_filename,
            "content_type": stored_file.content_type,
            "storage_path": stored_file.storage_path,
            "uploaded_at": stored_file.uploaded_at,
        },
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return DocumentUploadResponse.model_validate(document)


def list_documents_for_collection(
    db: Session, collection_id: int
) -> list[DocumentListItem]:
    get_collection(db, collection_id)
    statement = (
        select(Document)
        .where(Document.collection_id == collection_id)
        .options(selectinload(Document.collection), selectinload(Document.chunks))
        .order_by(Document.created_at.desc(), Document.id.desc())
    )
    documents = list(db.scalars(statement))
    return [serialize_document(document) for document in documents]


def get_document_detail(db: Session, document_id: int) -> DocumentDetailResponse:
    document = _get_document_model(db, document_id)
    return serialize_document_detail(document)


def delete_document(db: Session, document_id: int) -> None:
    document = _get_document_model(db, document_id)
    storage = LocalFileStorage()
    storage.delete_file(document.metadata_json.get("storage_path"))
    db.delete(document)
    db.commit()


def serialize_document(document: Document) -> DocumentListItem:
    uploaded_at_raw = document.metadata_json.get("uploaded_at")
    uploaded_at = _parse_uploaded_at(uploaded_at_raw)
    return DocumentListItem(
        id=document.id,
        filename=document.filename,
        source_type=document.source_type,
        status=document.status,
        collection=DocumentCollectionInfo(
            id=document.collection.id,
            name=document.collection.name,
        ),
        uploaded_at=uploaded_at,
        chunk_count=len(document.chunks),
        ingestion_metadata=document.metadata_json,
    )


def serialize_document_detail(document: Document) -> DocumentDetailResponse:
    summary = serialize_document(document)
    return DocumentDetailResponse(
        **summary.model_dump(),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _get_document_model(db: Session, document_id: int) -> Document:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.collection), selectinload(Document.chunks))
    )
    document = db.scalar(statement)
    if document is None:
        raise DocumentNotFoundError
    return document


def _parse_uploaded_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)

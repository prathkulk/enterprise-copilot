from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.app.models.document import Document
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


def upload_document(db: Session, collection_id: int, file: UploadFile) -> Document:
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
    return document

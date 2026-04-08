from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.ingestion_job import IngestionJob
from backend.app.schemas.documents import (
    DocumentIngestionResponse,
    IngestionJobResponse,
)
from backend.app.services.chunking import chunk_document
from backend.app.services.document_service import DocumentNotFoundError
from backend.app.services.embeddings import get_embedding_provider

embedding_provider = get_embedding_provider()


def ingest_document(db: Session, document_id: int) -> DocumentIngestionResponse:
    document = _get_document(db, document_id)
    job = IngestionJob(document_id=document_id, status="processing", error_message=None)
    db.add(job)

    try:
        document.status = "processing"
        db.commit()
        db.refresh(document)
        db.refresh(job)

        chunking_result = chunk_document(db, document_id)

        chunk_rows = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        )

        embeddings = embedding_provider.embed_documents([chunk.text for chunk in chunk_rows])
        for chunk, embedding in zip(chunk_rows, embeddings, strict=False):
            chunk.embedding = embedding

        document.status = "indexed"
        job.status = "indexed"
        job.error_message = None
        db.commit()
        db.refresh(document)
        db.refresh(job)

        return DocumentIngestionResponse(
            document_id=document.id,
            document_status=document.status,
            chunk_count=chunking_result.chunk_count,
            embedding_count=len(embeddings),
            ingestion_job=IngestionJobResponse.model_validate(job),
        )
    except Exception as exc:
        db.rollback()
        failed_document = _get_document(db, document_id)
        failed_document.status = "failed"
        db.add(failed_document)
        if job.id is not None:
            persisted_job = db.get(IngestionJob, job.id)
            if persisted_job is not None:
                persisted_job.status = "failed"
                persisted_job.error_message = str(exc)
        else:
            job.status = "failed"
            job.error_message = str(exc)
            db.add(job)
        db.commit()
        raise


def _get_document(db: Session, document_id: int) -> Document:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.chunks), selectinload(Document.ingestion_jobs))
    )
    document = db.scalar(statement)
    if document is None:
        raise DocumentNotFoundError
    return document

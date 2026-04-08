from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import SessionLocal
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.ingestion_job import IngestionJob
from backend.app.schemas.documents import (
    DocumentIngestionResponse,
    IngestionJobResponse,
)
from backend.app.schemas.jobs import (
    IngestionJobQueuedResponse,
    IngestionJobStatusResponse,
)
from backend.app.services.chunking import chunk_document
from backend.app.services.document_service import DocumentNotFoundError
from backend.app.services.embeddings import get_embedding_provider


class IngestionAlreadyRunningError(Exception):
    """Raised when a document already has an active ingestion job."""


class IngestionJobNotFoundError(Exception):
    """Raised when the requested ingestion job does not exist."""


def queue_ingestion_job(db: Session, document_id: int) -> IngestionJobQueuedResponse:
    document = _get_document(db, document_id)
    active_job = db.scalar(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .where(IngestionJob.status.in_(("pending", "processing")))
        .order_by(IngestionJob.created_at.desc())
    )
    if active_job is not None:
        raise IngestionAlreadyRunningError

    job = IngestionJob(document_id=document_id, status="pending", error_message=None)
    db.add(job)
    document.status = "uploaded"
    db.commit()
    db.refresh(job)
    return IngestionJobQueuedResponse.model_validate(job)


def run_ingestion_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        _process_ingestion_job(db=db, job_id=job_id)
    finally:
        db.close()


def _process_ingestion_job(db: Session, job_id: int) -> None:
    job = _get_job(db, job_id)
    document = _get_document(db, job.document_id)

    try:
        job.status = "processing"
        document.status = "processing"
        db.commit()
        db.refresh(document)
        db.refresh(job)

        chunking_result = chunk_document(db, job.document_id)

        chunk_rows = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == job.document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        )

        embedding_provider = get_embedding_provider()
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
        failed_document = _get_document(db, job.document_id)
        failed_document.status = "failed"
        db.add(failed_document)
        persisted_job = db.get(IngestionJob, job.id)
        if persisted_job is not None:
            persisted_job.status = "failed"
            persisted_job.error_message = str(exc)
        db.commit()


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


def get_ingestion_job_status(db: Session, job_id: int) -> IngestionJobStatusResponse:
    job = _get_job(db, job_id)
    document = _get_document(db, job.document_id)
    chunk_count = db.scalar(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document.id)
    )
    embedding_count = db.scalar(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document.id)
        .where(DocumentChunk.embedding.is_not(None))
    )
    return IngestionJobStatusResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        error_message=job.error_message,
        document_status=document.status,
        chunk_count=chunk_count or 0,
        embedding_count=embedding_count or 0,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _get_job(db: Session, job_id: int) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise IngestionJobNotFoundError
    return job

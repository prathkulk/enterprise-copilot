import logging
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.observability import log_event, request_id_context
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

logger = logging.getLogger("enterprise_copilot.ingestion")


class IngestionAlreadyRunningError(Exception):
    """Raised when a document already has an active ingestion job."""


class IngestionJobNotFoundError(Exception):
    """Raised when the requested ingestion job does not exist."""


def queue_ingestion_job(
    db: Session, document_id: int, tenant_id: int
) -> IngestionJobQueuedResponse:
    document = _get_document(db, document_id, tenant_id=tenant_id)
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
    log_event(
        logger,
        logging.INFO,
        "ingestion.queued",
        job_id=job.id,
        document_id=document.id,
        collection_id=document.collection_id,
        document_status=document.status,
    )
    return IngestionJobQueuedResponse.model_validate(job)


def run_ingestion_job(job_id: int, request_id: str | None = None) -> None:
    with request_id_context(request_id):
        db = SessionLocal()
        try:
            _process_ingestion_job(db=db, job_id=job_id)
        finally:
            db.close()


def _process_ingestion_job(db: Session, job_id: int) -> None:
    job = _get_job(db, job_id)
    document = _get_document(db, job.document_id)
    ingestion_started_at = perf_counter()

    try:
        job.status = "processing"
        document.status = "processing"
        db.commit()
        db.refresh(document)
        db.refresh(job)
        log_event(
            logger,
            logging.INFO,
            "ingestion.started",
            job_id=job.id,
            document_id=document.id,
            collection_id=document.collection_id,
        )

        chunking_started_at = perf_counter()
        chunking_result = chunk_document(db, job.document_id)
        chunking_duration_ms = round((perf_counter() - chunking_started_at) * 1000, 3)
        log_event(
            logger,
            logging.INFO,
            "ingestion.chunking.completed",
            job_id=job.id,
            document_id=document.id,
            collection_id=document.collection_id,
            chunk_count=chunking_result.chunk_count,
            chunking_duration_ms=chunking_duration_ms,
        )

        chunk_rows = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == job.document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        )

        embedding_provider = get_embedding_provider()
        embedding_started_at = perf_counter()
        embeddings = embedding_provider.embed_documents([chunk.text for chunk in chunk_rows])
        embedding_duration_ms = round((perf_counter() - embedding_started_at) * 1000, 3)
        for chunk, embedding in zip(chunk_rows, embeddings, strict=False):
            chunk.embedding = embedding
        log_event(
            logger,
            logging.INFO,
            "ingestion.embedding.completed",
            job_id=job.id,
            document_id=document.id,
            collection_id=document.collection_id,
            embedding_count=len(embeddings),
            embedding_duration_ms=embedding_duration_ms,
        )

        document.status = "indexed"
        job.status = "indexed"
        job.error_message = None
        db.commit()
        db.refresh(document)
        db.refresh(job)
        ingestion_duration_ms = round((perf_counter() - ingestion_started_at) * 1000, 3)
        log_event(
            logger,
            logging.INFO,
            "ingestion.completed",
            job_id=job.id,
            document_id=document.id,
            collection_id=document.collection_id,
            ingestion_duration_ms=ingestion_duration_ms,
            chunk_count=chunking_result.chunk_count,
            embedding_count=len(embeddings),
        )

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
        log_event(
            logger,
            logging.ERROR,
            "ingestion.failed",
            job_id=job.id,
            document_id=job.document_id,
            collection_id=failed_document.collection_id,
            ingestion_duration_ms=round((perf_counter() - ingestion_started_at) * 1000, 3),
            error=str(exc),
        )
        raise


def _get_document(
    db: Session, document_id: int, tenant_id: int | None = None
) -> Document:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.chunks), selectinload(Document.ingestion_jobs))
    )
    if tenant_id is not None:
        statement = statement.join(Document.collection).where(
            Document.collection.has(tenant_id=tenant_id)
        )
    document = db.scalar(statement)
    if document is None:
        raise DocumentNotFoundError
    return document


def get_ingestion_job_status(
    db: Session, job_id: int, tenant_id: int
) -> IngestionJobStatusResponse:
    job = _get_job(db, job_id, tenant_id=tenant_id)
    document = _get_document(db, job.document_id, tenant_id=tenant_id)
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


def _get_job(
    db: Session, job_id: int, tenant_id: int | None = None
) -> IngestionJob:
    statement = select(IngestionJob).where(IngestionJob.id == job_id)
    if tenant_id is not None:
        statement = statement.join(IngestionJob.document).join(Document.collection).where(
            Document.collection.has(tenant_id=tenant_id)
        )
    job = db.scalar(statement)
    if job is None:
        raise IngestionJobNotFoundError
    return job

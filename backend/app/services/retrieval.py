from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.collection import Collection
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.schemas.retrieval import (
    RetrievalCitation,
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
)
from backend.app.services.embeddings import get_embedding_provider


def retrieve_chunks(
    db: Session, payload: RetrievalRequest, tenant_id: int
) -> RetrievalResponse:
    embedding_provider = get_embedding_provider()
    query_embedding = embedding_provider.embed_query(payload.question)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    document_ids = _merged_document_ids(payload)

    statement = (
        select(DocumentChunk, distance.label("distance"))
        .join(DocumentChunk.document)
        .join(Document.collection)
        .options(
            joinedload(DocumentChunk.document).joinedload(Document.collection),
        )
        .where(DocumentChunk.embedding.is_not(None))
        .where(Collection.tenant_id == tenant_id)
    )

    if payload.collection_id is not None:
        statement = statement.where(Document.collection_id == payload.collection_id)
    if document_ids:
        statement = statement.where(Document.id.in_(document_ids))
    if payload.source_types:
        statement = statement.where(Document.source_type.in_(payload.source_types))
    if payload.tags:
        for tag in payload.tags:
            statement = statement.where(
                cast(Document.metadata_json["tags"], String).ilike(f"%{tag}%")
            )
    if payload.uploaded_from is not None:
        statement = statement.where(
            cast(Document.metadata_json["uploaded_at"], String)
            >= payload.uploaded_from.isoformat()
        )
    if payload.uploaded_to is not None:
        statement = statement.where(
            cast(Document.metadata_json["uploaded_at"], String)
            <= payload.uploaded_to.isoformat()
        )
    if payload.collection_name_contains is not None:
        statement = statement.where(
            Collection.name.ilike(f"%{payload.collection_name_contains}%")
        )
    if payload.collection_description_contains is not None:
        statement = statement.where(
            Collection.description.is_not(None),
            Collection.description.ilike(f"%{payload.collection_description_contains}%"),
        )

    statement = statement.order_by(distance).limit(payload.top_k)

    rows = db.execute(statement).all()
    results = [
        RetrievedChunk(
            score=round(max(0.0, 1.0 - float(distance_value)), 6),
            text=chunk.text,
            citation=RetrievalCitation(
                collection_id=chunk.document.collection.id,
                collection_name=chunk.document.collection.name,
                document_id=chunk.document.id,
                filename=chunk.document.filename,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                page_reference=chunk.metadata_json.get("page_reference"),
                start_char=chunk.metadata_json.get("start_char"),
                end_char=chunk.metadata_json.get("end_char"),
            ),
            metadata_json=chunk.metadata_json,
        )
        for chunk, distance_value in rows
    ]

    return RetrievalResponse(
        question=payload.question,
        top_k=payload.top_k,
        results=results,
    )


def _merged_document_ids(payload: RetrievalRequest) -> list[int] | None:
    merged_ids: list[int] = []
    if payload.document_id is not None:
        merged_ids.append(payload.document_id)
    if payload.document_ids:
        merged_ids.extend(payload.document_ids)

    unique_ids = list(dict.fromkeys(merged_ids))
    return unique_ids or None

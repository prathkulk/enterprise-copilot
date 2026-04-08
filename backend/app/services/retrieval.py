from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.schemas.retrieval import (
    RetrievalCitation,
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
)
from backend.app.services.embeddings import get_embedding_provider


def retrieve_chunks(db: Session, payload: RetrievalRequest) -> RetrievalResponse:
    embedding_provider = get_embedding_provider()
    query_embedding = embedding_provider.embed_query(payload.question)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(DocumentChunk, distance.label("distance"))
        .join(DocumentChunk.document)
        .options(
            joinedload(DocumentChunk.document).joinedload(Document.collection),
        )
        .where(DocumentChunk.embedding.is_not(None))
    )

    if payload.collection_id is not None:
        statement = statement.where(Document.collection_id == payload.collection_id)
    if payload.document_id is not None:
        statement = statement.where(Document.id == payload.document_id)

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

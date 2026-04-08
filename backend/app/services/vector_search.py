from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.collection import Collection
from backend.app.models.document_chunk import DocumentChunk


def find_similar_chunks(
    db: Session,
    query_embedding: Sequence[float],
    tenant_id: int,
    limit: int = 5,
) -> list[tuple[DocumentChunk, float]]:
    distance = DocumentChunk.embedding.cosine_distance(list(query_embedding))
    statement = (
        select(DocumentChunk, distance.label("distance"))
        .join(DocumentChunk.document)
        .join(Document.collection)
        .where(DocumentChunk.embedding.is_not(None))
        .where(Collection.tenant_id == tenant_id)
        .order_by(distance)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    return [(chunk, float(distance_value)) for chunk, distance_value in rows]

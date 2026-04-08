from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.document_chunk import DocumentChunk


def find_similar_chunks(
    db: Session, query_embedding: Sequence[float], limit: int = 5
) -> list[tuple[DocumentChunk, float]]:
    distance = DocumentChunk.embedding.cosine_distance(list(query_embedding))
    statement = (
        select(DocumentChunk, distance.label("distance"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    return [(chunk, float(distance_value)) for chunk, distance_value in rows]

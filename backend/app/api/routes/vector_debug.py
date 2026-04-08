from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db_session
from backend.app.models.collection import Collection
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.services.embeddings import get_embedding_provider
from backend.app.services.vector_search import find_similar_chunks

settings = get_settings()
embedding_provider = get_embedding_provider()

router = APIRouter(prefix="/debug/vector-search", tags=["debug"])


class MockChunkSeed(BaseModel):
    chunk_index: int
    text: str
    embedding: list[float] = Field(min_length=settings.embedding_dimensions)


class MockVectorSeedResponse(BaseModel):
    collection_id: int
    document_id: int
    chunk_ids: list[int]


class SimilarityQueryRequest(BaseModel):
    query_embedding: list[float] = Field(min_length=settings.embedding_dimensions)
    limit: int = Field(default=3, ge=1, le=20)


class SimilarityResult(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    text: str
    distance: float


class EmbeddingDebugRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=10)
    query_text: str | None = None


class EmbeddingDebugResponse(BaseModel):
    provider: str
    dimensions: int
    document_embeddings: list[list[float]]
    query_embedding: list[float] | None


DEFAULT_MOCK_CHUNKS = [
    MockChunkSeed(
        chunk_index=0,
        text="The alpha onboarding guide explains workspace setup and local development.",
        embedding=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    MockChunkSeed(
        chunk_index=1,
        text="The beta retrieval note covers embeddings, chunk scoring, and citations.",
        embedding=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    MockChunkSeed(
        chunk_index=2,
        text="The blended alpha-beta memo connects local setup with retrieval quality.",
        embedding=[0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
]


def validate_embedding_size(values: list[float]) -> None:
    if len(values) != settings.embedding_dimensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Embedding length must be exactly {settings.embedding_dimensions} "
                f"values."
            ),
        )


@router.post("/seed", response_model=MockVectorSeedResponse, status_code=status.HTTP_201_CREATED)
def seed_mock_vectors(db: Session = Depends(get_db_session)) -> MockVectorSeedResponse:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    collection = Collection(
        name=f"Vector Debug Collection {timestamp}",
        description="Temporary collection for pgvector similarity verification.",
    )
    document = Document(
        collection=collection,
        filename=f"vector-debug-{timestamp}.txt",
        source_type="debug",
        status="ready",
        metadata_json={"seeded_for": "vector_search_debug"},
    )
    db.add_all([collection, document])
    db.flush()

    chunks: list[DocumentChunk] = []
    for mock_chunk in DEFAULT_MOCK_CHUNKS:
        validate_embedding_size(mock_chunk.embedding)
        chunk = DocumentChunk(
            document=document,
            chunk_index=mock_chunk.chunk_index,
            text=mock_chunk.text,
            metadata_json={"seeded": True},
            embedding=mock_chunk.embedding,
        )
        db.add(chunk)
        chunks.append(chunk)

    db.commit()

    return MockVectorSeedResponse(
        collection_id=collection.id,
        document_id=document.id,
        chunk_ids=[chunk.id for chunk in chunks],
    )


@router.post("/query", response_model=list[SimilarityResult])
def query_similar_chunks(
    payload: SimilarityQueryRequest, db: Session = Depends(get_db_session)
) -> list[SimilarityResult]:
    validate_embedding_size(payload.query_embedding)
    results = find_similar_chunks(
        db=db,
        query_embedding=payload.query_embedding,
        limit=payload.limit,
    )
    return [
        SimilarityResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            distance=distance,
        )
        for chunk, distance in results
    ]


@router.post("/embeddings", response_model=EmbeddingDebugResponse)
def debug_embeddings(payload: EmbeddingDebugRequest) -> EmbeddingDebugResponse:
    document_embeddings = embedding_provider.embed_documents(payload.texts)
    query_embedding = (
        embedding_provider.embed_query(payload.query_text)
        if payload.query_text is not None
        else None
    )
    return EmbeddingDebugResponse(
        provider=embedding_provider.provider_name,
        dimensions=settings.embedding_dimensions,
        document_embeddings=document_embeddings,
        query_embedding=query_embedding,
    )

from time import perf_counter

from sqlalchemy.orm import Session

from backend.app.schemas.ask import (
    AskLatency,
    AskProviderMetadata,
    AskRequest,
    AskResponse,
)
from backend.app.schemas.retrieval import RetrievalRequest
from backend.app.services.answer_generation import generate_answer_from_chunks
from backend.app.services.llm import get_llm_provider
from backend.app.services.embeddings import get_embedding_provider
from backend.app.services.retrieval import retrieve_chunks


def ask_question(payload: AskRequest, db: Session) -> AskResponse:
    total_started_at = perf_counter()

    retrieval_started_at = perf_counter()
    retrieval_response = retrieve_chunks(
        db=db,
        payload=RetrievalRequest(
            question=payload.question,
            collection_id=payload.collection_id,
            document_id=payload.document_id,
            top_k=payload.top_k,
        ),
    )
    retrieval_duration_ms = round((perf_counter() - retrieval_started_at) * 1000, 3)

    answer_started_at = perf_counter()
    answer_response = generate_answer_from_chunks(
        question=payload.question,
        retrieved_chunks=retrieval_response.results,
    )
    answer_duration_ms = round((perf_counter() - answer_started_at) * 1000, 3)
    total_duration_ms = round((perf_counter() - total_started_at) * 1000, 3)

    return AskResponse(
        question=payload.question,
        collection_id=payload.collection_id,
        document_id=payload.document_id,
        top_k=payload.top_k,
        answer=answer_response.answer,
        confidence=answer_response.confidence,
        insufficient_evidence=answer_response.insufficient_evidence,
        citations=answer_response.citations,
        retrieved_chunks=retrieval_response.results,
        latency_ms=AskLatency(
            total_ms=total_duration_ms,
            retrieval_ms=retrieval_duration_ms,
            answer_generation_ms=answer_duration_ms,
        ),
        providers=AskProviderMetadata(
            embedding_provider=get_embedding_provider().provider_name,
            llm_provider=get_llm_provider().provider_name,
        ),
    )

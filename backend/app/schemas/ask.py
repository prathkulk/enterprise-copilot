from pydantic import BaseModel

from backend.app.schemas.answers import AnswerCitation
from backend.app.schemas.retrieval import RetrievedChunk, RetrievalRequest


class AskRequest(RetrievalRequest):
    pass


class AskLatency(BaseModel):
    total_ms: float
    retrieval_ms: float
    answer_generation_ms: float


class AskProviderMetadata(BaseModel):
    embedding_provider: str
    llm_provider: str


class AskResponse(BaseModel):
    question: str
    collection_id: int | None
    document_id: int | None
    top_k: int
    answer: str
    confidence: str
    insufficient_evidence: bool
    citations: list[AnswerCitation]
    retrieved_chunks: list[RetrievedChunk]
    latency_ms: AskLatency
    providers: AskProviderMetadata

from typing import Literal

from pydantic import BaseModel

from backend.app.schemas.retrieval import RetrievalCitation, RetrievalRequest


class AnswerRequest(RetrievalRequest):
    pass


class AnswerCitation(RetrievalCitation):
    index: int
    marker: str
    label: str
    score: float


class AnswerResponse(BaseModel):
    question: str
    answer: str
    confidence: Literal["grounded", "insufficient_evidence"]
    insufficient_evidence: bool
    citations: list[AnswerCitation]

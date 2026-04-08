from typing import Any

from pydantic import BaseModel, Field, model_validator


class RetrievalRequest(BaseModel):
    question: str = Field(min_length=1)
    collection_id: int | None = None
    document_id: int | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def ensure_filter_present(self) -> "RetrievalRequest":
        if self.collection_id is None and self.document_id is None:
            raise ValueError("Either collection_id or document_id must be provided.")
        return self


class RetrievalCitation(BaseModel):
    collection_id: int
    collection_name: str
    document_id: int
    filename: str
    chunk_id: int
    chunk_index: int
    page_reference: int | list[int] | None
    start_char: int | None
    end_char: int | None


class RetrievedChunk(BaseModel):
    score: float
    text: str
    citation: RetrievalCitation
    metadata_json: dict[str, Any]


class RetrievalResponse(BaseModel):
    question: str
    top_k: int
    results: list[RetrievedChunk]

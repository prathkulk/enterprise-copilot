from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class RetrievalRequestBase(BaseModel):
    question: str = Field(min_length=1)
    collection_id: int | None = None
    document_id: int | None = None
    document_ids: list[int] | None = None
    tags: list[str] | None = None
    uploaded_from: datetime | None = None
    uploaded_to: datetime | None = None
    source_types: list[str] | None = None
    collection_name_contains: str | None = None
    collection_description_contains: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator(
        "document_ids",
        "tags",
        "source_types",
        mode="before",
    )
    @classmethod
    def normalize_list_filters(
        cls, value: list[str] | list[int] | None
    ) -> list[str] | list[int] | None:
        if value is None:
            return None
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, str):
                    stripped = item.strip()
                    if stripped:
                        normalized.append(stripped)
                else:
                    normalized.append(item)
            return normalized or None
        return value

    @field_validator("collection_name_contains", "collection_description_contains")
    @classmethod
    def normalize_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def has_scope_filter(self) -> bool:
        return any(
            (
                self.collection_id is not None,
                self.document_id is not None,
                self.document_ids,
                self.tags,
                self.uploaded_from is not None,
                self.uploaded_to is not None,
                self.source_types,
                self.collection_name_contains is not None,
                self.collection_description_contains is not None,
            )
        )

    @model_validator(mode="after")
    def validate_date_range(self) -> "RetrievalRequestBase":
        if self.uploaded_from and self.uploaded_to and self.uploaded_from > self.uploaded_to:
            raise ValueError("uploaded_from must be earlier than or equal to uploaded_to.")
        return self


class RetrievalRequest(RetrievalRequestBase):
    @model_validator(mode="after")
    def ensure_filter_present(self) -> "RetrievalRequest":
        if not self.has_scope_filter():
            raise ValueError("At least one retrieval filter must be provided.")

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

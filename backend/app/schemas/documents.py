from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentCollectionInfo(BaseModel):
    id: int
    name: str


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    filename: str
    source_type: str
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentListItem(BaseModel):
    id: int
    filename: str
    source_type: str
    status: str
    collection: DocumentCollectionInfo
    uploaded_at: datetime | None
    chunk_count: int
    ingestion_metadata: dict[str, Any]


class DocumentDetailResponse(DocumentListItem):
    created_at: datetime
    updated_at: datetime


class DocumentExtractionResponse(BaseModel):
    document_id: int
    filename: str
    source_type: str
    extracted_text: str
    parser_metadata: dict[str, Any]


class DocumentChunkResponse(BaseModel):
    chunk_index: int
    text: str
    metadata_json: dict[str, Any]


class DocumentChunkingResponse(BaseModel):
    document_id: int
    filename: str
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    chunk_min_length: int
    chunks: list[DocumentChunkResponse]


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentIngestionResponse(BaseModel):
    document_id: int
    document_status: str
    chunk_count: int
    embedding_count: int
    ingestion_job: IngestionJobResponse

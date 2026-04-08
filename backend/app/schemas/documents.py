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

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionJobQueuedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class IngestionJobStatusResponse(BaseModel):
    id: int
    document_id: int
    status: str
    error_message: str | None
    document_status: str
    chunk_count: int
    embedding_count: int
    created_at: datetime
    updated_at: datetime

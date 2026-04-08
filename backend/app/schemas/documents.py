from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    filename: str
    source_type: str
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

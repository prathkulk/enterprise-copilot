from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.models.collection import Collection

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate, db: Session = Depends(get_db_session)
) -> Collection:
    collection = Collection(name=payload.name, description=payload.description)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: int, db: Session = Depends(get_db_session)
) -> Collection:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return collection

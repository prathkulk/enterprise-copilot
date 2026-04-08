from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.models.user import User
from backend.app.schemas.collections import (
    CollectionCreate,
    CollectionResponse,
    CollectionUpdate,
)
from backend.app.services.auth_service import get_current_user
from backend.app.services.collection_service import (
    CollectionConflictError,
    CollectionNotFoundError,
    create_collection as create_collection_record,
    delete_collection as delete_collection_record,
    get_collection as get_collection_record,
    list_collections as list_collection_records,
    update_collection as update_collection_record,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return create_collection_record(db, payload, current_user.tenant_id)
    except CollectionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A collection with that name already exists.",
        ) from exc


@router.get("", response_model=list[CollectionResponse])
def list_collections(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    return list_collection_records(db, current_user.tenant_id)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_collection_record(db, collection_id, current_user.tenant_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    payload: CollectionUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return update_collection_record(db, collection_id, payload, current_user.tenant_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc
    except CollectionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A collection with that name already exists.",
        ) from exc


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_collection_record(db, collection_id, current_user.tenant_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

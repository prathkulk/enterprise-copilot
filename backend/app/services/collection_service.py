from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.collection import Collection
from backend.app.schemas.collections import CollectionCreate, CollectionUpdate


class CollectionNotFoundError(Exception):
    """Raised when the requested collection does not exist."""


class CollectionConflictError(Exception):
    """Raised when a collection update would violate uniqueness."""


def create_collection(db: Session, payload: CollectionCreate, tenant_id: int) -> Collection:
    collection = Collection(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(collection)
    return _commit_and_refresh(db, collection)


def list_collections(db: Session, tenant_id: int) -> list[Collection]:
    statement = (
        select(Collection)
        .where(Collection.tenant_id == tenant_id)
        .order_by(Collection.created_at.desc(), Collection.id.desc())
    )
    return list(db.scalars(statement))


def get_collection(db: Session, collection_id: int, tenant_id: int) -> Collection:
    collection = db.scalar(
        select(Collection)
        .where(Collection.id == collection_id)
        .where(Collection.tenant_id == tenant_id)
    )
    if collection is None:
        raise CollectionNotFoundError
    return collection


def update_collection(
    db: Session, collection_id: int, payload: CollectionUpdate, tenant_id: int
) -> Collection:
    collection = get_collection(db, collection_id, tenant_id)
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(collection, field, value)

    return _commit_and_refresh(db, collection)


def delete_collection(db: Session, collection_id: int, tenant_id: int) -> None:
    collection = get_collection(db, collection_id, tenant_id)
    db.delete(collection)
    db.commit()


def _commit_and_refresh(db: Session, collection: Collection) -> Collection:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CollectionConflictError from exc
    db.refresh(collection)
    return collection

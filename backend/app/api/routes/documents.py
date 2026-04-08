from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.documents import DocumentResponse
from backend.app.services.collection_service import CollectionNotFoundError
from backend.app.services.document_service import (
    UnsupportedDocumentTypeError,
    upload_document as upload_document_record,
)

router = APIRouter(tags=["documents"])


@router.post(
    "/collections/{collection_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    collection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
):
    try:
        return upload_document_record(db=db, collection_id=collection_id, file=file)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

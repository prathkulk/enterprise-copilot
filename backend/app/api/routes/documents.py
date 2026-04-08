from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.documents import (
    DocumentDetailResponse,
    DocumentExtractionResponse,
    DocumentListItem,
    DocumentUploadResponse,
)
from backend.app.services.collection_service import CollectionNotFoundError
from backend.app.services.document_service import (
    DocumentNotFoundError,
    UnsupportedDocumentTypeError,
    delete_document as delete_document_record,
    get_document_detail as get_document_detail_record,
    list_documents_for_collection as list_documents_for_collection_records,
    upload_document as upload_document_record,
)
from backend.app.services.text_extraction import (
    DocumentExtractionNotAvailableError,
    extract_document_text as extract_document_text_record,
)

router = APIRouter(tags=["documents"])


@router.post(
    "/collections/{collection_id}/documents/upload",
    response_model=DocumentUploadResponse,
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


@router.get(
    "/collections/{collection_id}/documents",
    response_model=list[DocumentListItem],
)
def list_collection_documents(
    collection_id: int, db: Session = Depends(get_db_session)
):
    try:
        return list_documents_for_collection_records(db=db, collection_id=collection_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: int, db: Session = Depends(get_db_session)):
    try:
        return get_document_detail_record(db=db, document_id=document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db_session)) -> Response:
    try:
        delete_document_record(db=db, document_id=document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/extract",
    response_model=DocumentExtractionResponse,
)
def extract_document_text(document_id: int, db: Session = Depends(get_db_session)):
    try:
        return extract_document_text_record(db=db, document_id=document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc
    except DocumentExtractionNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

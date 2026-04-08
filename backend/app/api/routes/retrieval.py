from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from backend.app.services.retrieval import retrieve_chunks

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(payload: RetrievalRequest, db: Session = Depends(get_db_session)):
    return retrieve_chunks(db=db, payload=payload)

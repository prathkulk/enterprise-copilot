from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.answers import AnswerRequest, AnswerResponse
from backend.app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from backend.app.services.answer_generation import generate_answer
from backend.app.services.llm import LLMProviderError
from backend.app.services.retrieval import retrieve_chunks

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(payload: RetrievalRequest, db: Session = Depends(get_db_session)):
    return retrieve_chunks(db=db, payload=payload)


@router.post("/answer", response_model=AnswerResponse)
def answer(payload: AnswerRequest, db: Session = Depends(get_db_session)):
    try:
        return generate_answer(payload=payload, db=db)
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc

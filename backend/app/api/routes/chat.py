from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionMessagesResponse,
    ChatSessionResponse,
    SessionAskRequest,
    SessionAskResponse,
)
from backend.app.services.chat_service import (
    ChatSessionNotFoundError,
    ask_within_session,
    create_chat_session,
    list_session_messages,
)
from backend.app.services.collection_service import CollectionNotFoundError
from backend.app.services.embeddings import EmbeddingProviderError
from backend.app.services.llm import LLMProviderError

router = APIRouter(tags=["chat"])


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: ChatSessionCreate, db: Session = Depends(get_db_session)
):
    try:
        return create_chat_session(db=db, payload=payload)
    except CollectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        ) from exc


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatSessionMessagesResponse,
)
def get_session_messages(session_id: int, db: Session = Depends(get_db_session)):
    try:
        return list_session_messages(db=db, session_id=session_id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        ) from exc


@router.post(
    "/sessions/{session_id}/ask",
    response_model=SessionAskResponse,
)
def ask_in_session(
    session_id: int,
    payload: SessionAskRequest,
    db: Session = Depends(get_db_session),
):
    try:
        return ask_within_session(db=db, session_id=session_id, payload=payload)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        ) from exc
    except (EmbeddingProviderError, LLMProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

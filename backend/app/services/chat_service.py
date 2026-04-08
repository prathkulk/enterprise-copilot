from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from backend.app.models.chat_message import ChatMessage
from backend.app.models.chat_session import ChatSession
from backend.app.models.message_feedback import MessageFeedback
from backend.app.schemas.ask import AskRequest
from backend.app.schemas.chat import (
    ChatMessageResponse,
    MessageFeedbackCreate,
    MessageFeedbackResponse,
    ChatSessionCreate,
    ChatSessionMessagesResponse,
    ChatSessionResponse,
    SessionAskRequest,
    SessionAskResponse,
)
from backend.app.services.ask import run_ask_question
from backend.app.services.collection_service import get_collection
from backend.app.services.conversation_rewrite import rewrite_query_with_history


class ChatSessionNotFoundError(Exception):
    """Raised when the requested chat session does not exist."""


class ChatMessageNotFoundError(Exception):
    """Raised when the requested chat message does not exist."""


class InvalidFeedbackTargetError(Exception):
    """Raised when feedback targets a non-assistant message."""


def create_chat_session(db: Session, payload: ChatSessionCreate) -> ChatSessionResponse:
    if payload.collection_id is not None:
        get_collection(db, payload.collection_id)

    session = ChatSession(title=payload.title, collection_id=payload.collection_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _serialize_session(session)


def list_session_messages(
    db: Session, session_id: int
) -> ChatSessionMessagesResponse:
    session = _get_chat_session(db, session_id)
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    messages = list(db.scalars(statement))
    return ChatSessionMessagesResponse(
        session=_serialize_session(session),
        messages=[_serialize_message(message) for message in messages],
    )


def ask_within_session(
    db: Session, session_id: int, payload: SessionAskRequest
) -> SessionAskResponse:
    session = _get_chat_session(db, session_id)
    prior_messages = _list_session_message_models(db, session.id)
    effective_collection_id = payload.collection_id or session.collection_id
    try:
        ask_payload = AskRequest(
            question=payload.question,
            collection_id=effective_collection_id,
            document_id=payload.document_id,
            document_ids=payload.document_ids,
            tags=payload.tags,
            uploaded_from=payload.uploaded_from,
            uploaded_to=payload.uploaded_to,
            source_types=payload.source_types,
            collection_name_contains=payload.collection_name_contains,
            collection_description_contains=payload.collection_description_contains,
            top_k=payload.top_k,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    rewrite_result = rewrite_query_with_history(
        question=payload.question,
        history=prior_messages,
    )
    ask_execution = run_ask_question(
        payload=ask_payload,
        db=db,
        retrieval_question=rewrite_result.rewritten_question,
    )
    ask_response = ask_execution.response
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=ask_payload.question,
        citations_json=[],
        metadata_json={
            "collection_id": ask_payload.collection_id,
            "document_id": ask_payload.document_id,
            "document_ids": ask_payload.document_ids,
            "tags": ask_payload.tags,
            "uploaded_from": (
                ask_payload.uploaded_from.isoformat()
                if ask_payload.uploaded_from is not None
                else None
            ),
            "uploaded_to": (
                ask_payload.uploaded_to.isoformat()
                if ask_payload.uploaded_to is not None
                else None
            ),
            "source_types": ask_payload.source_types,
            "collection_name_contains": ask_payload.collection_name_contains,
            "collection_description_contains": ask_payload.collection_description_contains,
            "top_k": ask_payload.top_k,
            "rewritten_question": ask_execution.retrieval_question,
            "rewrite_applied": rewrite_result.rewrite_applied,
            "rewrite_prompt_version": rewrite_result.prompt_version,
            "rewrite_history_messages_used": rewrite_result.history_messages_used,
        },
    )
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=ask_response.answer,
        citations_json=[citation.model_dump() for citation in ask_response.citations],
        metadata_json={
            "confidence": ask_response.confidence,
            "insufficient_evidence": ask_response.insufficient_evidence,
            "missing_information": ask_response.missing_information,
            "answer_mode": ask_response.answer_mode,
            "prompt_version": ask_response.prompt_version,
            "latency_ms": ask_response.latency_ms.model_dump(),
            "providers": ask_response.providers.model_dump(),
            "rewritten_question": ask_execution.retrieval_question,
            "rewrite_applied": rewrite_result.rewrite_applied,
            "rewrite_prompt_version": rewrite_result.prompt_version,
            "rewrite_history_messages_used": rewrite_result.history_messages_used,
            "retrieved_chunks": [
                chunk.model_dump() for chunk in ask_response.retrieved_chunks
            ],
        },
    )
    db.add(user_message)
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return SessionAskResponse(
        session_id=session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        rewritten_question=ask_execution.retrieval_question,
        rewrite_applied=rewrite_result.rewrite_applied,
        rewrite_prompt_version=rewrite_result.prompt_version,
        rewrite_history_messages_used=rewrite_result.history_messages_used,
        **ask_response.model_dump(),
    )


def submit_message_feedback(
    db: Session, message_id: int, payload: MessageFeedbackCreate
) -> MessageFeedbackResponse:
    message = _get_chat_message(db, message_id)
    if message.role != "assistant":
        raise InvalidFeedbackTargetError

    feedback = MessageFeedback(
        message_id=message.id,
        signal=payload.signal,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return _serialize_feedback(feedback)


def _get_chat_session(db: Session, session_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise ChatSessionNotFoundError
    return session


def _get_chat_message(db: Session, message_id: int) -> ChatMessage:
    message = db.get(ChatMessage, message_id)
    if message is None:
        raise ChatMessageNotFoundError
    return message


def _list_session_message_models(db: Session, session_id: int) -> list[ChatMessage]:
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    return list(db.scalars(statement))


def _serialize_session(session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        collection_id=session.collection_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _serialize_message(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        citations=message.citations_json,
        metadata_json=message.metadata_json,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _serialize_feedback(feedback: MessageFeedback) -> MessageFeedbackResponse:
    return MessageFeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        signal=feedback.signal,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )

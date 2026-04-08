from dataclasses import dataclass

from backend.app.core.config import get_settings
from backend.app.models.chat_message import ChatMessage
from backend.app.prompts import (
    QUERY_REWRITE_PROMPT_VERSION,
    QueryRewriteHistoryTurn,
    QueryRewritePrompt,
    build_query_rewrite_prompt,
)
from backend.app.services.llm import get_llm_provider
from backend.app.services.llm import heuristic_rewrite_query_with_history

settings = get_settings()


@dataclass(frozen=True)
class ConversationRewriteResult:
    original_question: str
    rewritten_question: str
    rewrite_applied: bool
    prompt_version: str
    history_messages_used: int


def rewrite_query_with_history(
    *, question: str, history: list[ChatMessage]
) -> ConversationRewriteResult:
    normalized_question = question.strip()
    relevant_history = _recent_history(history)
    if not relevant_history:
        return ConversationRewriteResult(
            original_question=normalized_question,
            rewritten_question=normalized_question,
            rewrite_applied=False,
            prompt_version=QUERY_REWRITE_PROMPT_VERSION,
            history_messages_used=0,
        )

    prompt_bundle = build_query_rewrite_prompt(
        QueryRewritePrompt(
            question=normalized_question,
            history=[
                QueryRewriteHistoryTurn(role=message.role, content=message.content)
                for message in relevant_history
            ],
        )
    )
    draft = get_llm_provider().rewrite_query_with_history(
        prompt_bundle=prompt_bundle,
        question=normalized_question,
        history=[
            QueryRewriteHistoryTurn(role=message.role, content=message.content)
            for message in relevant_history
        ],
    )
    if (
        not draft.rewrite_applied
        or draft.standalone_question.strip().lower() == normalized_question.lower()
    ):
        fallback_draft = heuristic_rewrite_query_with_history(
            question=normalized_question,
            history=[
                QueryRewriteHistoryTurn(role=message.role, content=message.content)
                for message in relevant_history
            ],
        )
        if fallback_draft.rewrite_applied:
            draft = fallback_draft

    rewritten_question = draft.standalone_question.strip() or normalized_question
    rewrite_applied = (
        draft.rewrite_applied
        and rewritten_question.lower() != normalized_question.lower()
    )
    return ConversationRewriteResult(
        original_question=normalized_question,
        rewritten_question=rewritten_question,
        rewrite_applied=rewrite_applied,
        prompt_version=prompt_bundle.version,
        history_messages_used=len(relevant_history),
    )


def _recent_history(history: list[ChatMessage]) -> list[ChatMessage]:
    if not history:
        return []
    limit = max(0, settings.query_rewrite_history_messages)
    if limit == 0:
        return []
    return history[-limit:]

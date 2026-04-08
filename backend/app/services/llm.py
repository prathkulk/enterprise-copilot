from abc import ABC, abstractmethod
from functools import lru_cache
import json
import os
import re
from dataclasses import dataclass
from typing import Sequence

from backend.app.prompts import (
    GroundedAnswerPromptBundle,
    QueryRewriteHistoryTurn,
    QueryRewritePromptBundle,
)
from backend.app.core.config import get_settings
from backend.app.schemas.retrieval import RetrievedChunk

settings = get_settings()


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _split_sentences(text: str) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]
    return sentences or [text.strip()]


class LLMProviderError(Exception):
    pass


@dataclass(frozen=True)
class GroundedAnswerDraft:
    answer: str
    insufficient_evidence: bool
    missing_information: list[str]


@dataclass(frozen=True)
class QueryRewriteDraft:
    standalone_question: str
    rewrite_applied: bool


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate_grounded_answer(
        self,
        *,
        prompt_bundle: GroundedAnswerPromptBundle,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> GroundedAnswerDraft:
        raise NotImplementedError

    @abstractmethod
    def rewrite_query_with_history(
        self,
        *,
        prompt_bundle: QueryRewritePromptBundle,
        question: str,
        history: Sequence[QueryRewriteHistoryTurn],
    ) -> QueryRewriteDraft:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    provider_name = "mock"
    model_name = "mock-answer-v1"

    def generate_grounded_answer(
        self,
        *,
        prompt_bundle: GroundedAnswerPromptBundle,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> GroundedAnswerDraft:
        del prompt_bundle

        question_tokens = _tokenize(question)
        sections: list[str] = []
        seen_sections: set[str] = set()
        covered_tokens: set[str] = set()

        for chunk in chunks:
            sentences = _split_sentences(chunk.text)
            selected_sentence = sentences[0]

            for sentence in sentences:
                sentence_tokens = _tokenize(sentence)
                if question_tokens.intersection(sentence_tokens):
                    selected_sentence = sentence
                    covered_tokens.update(question_tokens.intersection(sentence_tokens))
                    break

            cleaned_sentence = selected_sentence.strip()
            if not cleaned_sentence:
                continue
            if cleaned_sentence[-1] not in ".!?":
                cleaned_sentence = f"{cleaned_sentence}."

            dedupe_key = cleaned_sentence.lower()
            if dedupe_key in seen_sections:
                continue

            seen_sections.add(dedupe_key)
            sections.append(cleaned_sentence)

        missing_tokens = sorted(
            token
            for token in question_tokens
            if token not in covered_tokens and len(token) > 4
        )
        missing_information = (
            [f"The documents do not cover {', '.join(missing_tokens[:3])} in enough detail."]
            if sections and len(missing_tokens) >= 2
            else []
        )

        if not sections:
            return GroundedAnswerDraft(
                answer="I do not have enough evidence in the indexed documents to answer that confidently.",
                insufficient_evidence=True,
                missing_information=[],
            )

        return GroundedAnswerDraft(
            answer=" ".join(sections).strip(),
            insufficient_evidence=False,
            missing_information=missing_information,
        )

    def rewrite_query_with_history(
        self,
        *,
        prompt_bundle: QueryRewritePromptBundle,
        question: str,
        history: Sequence[QueryRewriteHistoryTurn],
    ) -> QueryRewriteDraft:
        del prompt_bundle
        return heuristic_rewrite_query_with_history(question=question, history=history)


class OpenAILLMProvider(LLMProvider):
    provider_name = "openai"
    model_name = settings.llm_model

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured.")

        from openai import OpenAI

        client_kwargs = {"api_key": api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self._client = OpenAI(**client_kwargs)
        return self._client

    def generate_grounded_answer(
        self,
        *,
        prompt_bundle: GroundedAnswerPromptBundle,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> GroundedAnswerDraft:
        del question, chunks

        try:
            response = self._get_client().responses.create(
                model=settings.llm_model,
                input=prompt_bundle.prompt,
            )
        except Exception as exc:
            raise LLMProviderError(_format_openai_error(exc)) from exc
        output_text = response.output_text.strip()
        if not output_text:
            raise LLMProviderError("OpenAI response did not contain text output.")
        return _parse_grounded_answer(output_text)

    def rewrite_query_with_history(
        self,
        *,
        prompt_bundle: QueryRewritePromptBundle,
        question: str,
        history: Sequence[QueryRewriteHistoryTurn],
    ) -> QueryRewriteDraft:
        del question, history

        try:
            response = self._get_client().responses.create(
                model=settings.llm_model,
                input=prompt_bundle.prompt,
            )
        except Exception as exc:
            raise LLMProviderError(_format_openai_error(exc)) from exc
        output_text = response.output_text.strip()
        if not output_text:
            raise LLMProviderError("OpenAI response did not contain text output.")
        return _parse_query_rewrite(output_text)


class PlaceholderLLMProvider(LLMProvider):
    provider_name = "placeholder"
    model_name = "unconfigured"

    def generate_grounded_answer(
        self,
        *,
        prompt_bundle: GroundedAnswerPromptBundle,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> GroundedAnswerDraft:
        del prompt_bundle, question, chunks
        raise LLMProviderError("Real LLM provider integration is not configured yet.")

    def rewrite_query_with_history(
        self,
        *,
        prompt_bundle: QueryRewritePromptBundle,
        question: str,
        history: Sequence[QueryRewriteHistoryTurn],
    ) -> QueryRewriteDraft:
        del prompt_bundle, question, history
        raise LLMProviderError("Real LLM provider integration is not configured yet.")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    providers: dict[str, LLMProvider] = {
        "openai": OpenAILLMProvider(),
        "mock": MockLLMProvider(),
        "placeholder": PlaceholderLLMProvider(),
    }
    return providers.get(settings.llm_provider, OpenAILLMProvider())


def _format_openai_error(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        return f"OpenAI response request failed ({status_code}): {exc}"
    return f"OpenAI response request failed: {exc}"


def _parse_grounded_answer(output_text: str) -> GroundedAnswerDraft:
    cleaned = output_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        raise LLMProviderError("OpenAI response did not return valid structured JSON.")

    answer = str(payload.get("answer", "")).strip()
    insufficient_evidence = bool(payload.get("insufficient_evidence", False))
    raw_missing_information = payload.get("missing_information", [])
    if not isinstance(raw_missing_information, list):
        raw_missing_information = []
    missing_information = [
        str(item).strip()
        for item in raw_missing_information
        if str(item).strip()
    ]

    return GroundedAnswerDraft(
        answer=answer,
        insufficient_evidence=insufficient_evidence,
        missing_information=missing_information,
    )


def _parse_query_rewrite(output_text: str) -> QueryRewriteDraft:
    cleaned = output_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMProviderError(
            "OpenAI response did not return valid rewrite JSON."
        ) from exc

    standalone_question = str(payload.get("standalone_question", "")).strip()
    rewrite_applied = bool(payload.get("rewrite_applied", False))
    return QueryRewriteDraft(
        standalone_question=standalone_question,
        rewrite_applied=rewrite_applied,
    )


def heuristic_rewrite_query_with_history(
    *, question: str, history: Sequence[QueryRewriteHistoryTurn]
) -> QueryRewriteDraft:
    normalized_question = question.strip()
    prior_user_question = _last_user_question(history)
    if not prior_user_question:
        return QueryRewriteDraft(
            standalone_question=normalized_question,
            rewrite_applied=False,
        )

    rewritten_question = _rewrite_follow_up_question(
        normalized_question, prior_user_question
    )
    return QueryRewriteDraft(
        standalone_question=rewritten_question,
        rewrite_applied=rewritten_question.lower() != normalized_question.lower(),
    )


FOLLOW_UP_PREFIXES = (
    "what about ",
    "how about ",
    "and ",
    "what if ",
    "what about",
    "how about",
)
FOLLOW_UP_PRONOUNS = {
    "it",
    "they",
    "them",
    "those",
    "these",
    "that",
    "their",
    "its",
}


def _last_user_question(history: Sequence[QueryRewriteHistoryTurn]) -> str | None:
    for turn in reversed(history):
        if turn.role == "user" and turn.content.strip():
            return turn.content.strip()
    return None


def _rewrite_follow_up_question(question: str, prior_user_question: str) -> str:
    normalized_question = question.strip()
    lowered_question = normalized_question.lower()
    prior_stem = prior_user_question.strip().rstrip("?.! ")
    if not prior_stem:
        return normalized_question

    for prefix in FOLLOW_UP_PREFIXES:
        if lowered_question.startswith(prefix):
            tail = normalized_question[len(prefix) :].strip(" ?.")
            if tail:
                return f"{prior_stem} for {tail}?"
            return normalized_question

    question_tokens = _tokenize(normalized_question)
    if question_tokens.intersection(FOLLOW_UP_PRONOUNS):
        return f"{normalized_question.rstrip('?.!')} in relation to {prior_stem}?"

    if len(question_tokens) <= 4 and prior_stem:
        return f"{prior_stem} with respect to {normalized_question.rstrip('?.!')}?"

    return normalized_question

from abc import ABC, abstractmethod
from functools import lru_cache
import json
import os
import re
from dataclasses import dataclass
from typing import Sequence

from backend.app.prompts import GroundedAnswerPromptBundle
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
            if token not in covered_tokens and len(token) > 3
        )
        missing_information = (
            [f"The indexed documents do not specify details about: {', '.join(missing_tokens[:5])}."]
            if sections and missing_tokens
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

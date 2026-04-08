from abc import ABC, abstractmethod
import re
from typing import Sequence

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


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_answer_sections(
        self,
        *,
        prompt: str,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> list[str]:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    provider_name = "mock"

    def generate_answer_sections(
        self,
        *,
        prompt: str,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> list[str]:
        del prompt

        question_tokens = _tokenize(question)
        sections: list[str] = []
        seen_sections: set[str] = set()

        for chunk in chunks:
            sentences = _split_sentences(chunk.text)
            selected_sentence = sentences[0]

            for sentence in sentences:
                sentence_tokens = _tokenize(sentence)
                if question_tokens.intersection(sentence_tokens):
                    selected_sentence = sentence
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

        return sections


class PlaceholderLLMProvider(LLMProvider):
    provider_name = "placeholder"

    def generate_answer_sections(
        self,
        *,
        prompt: str,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> list[str]:
        del prompt, question, chunks
        raise LLMProviderError("Real LLM provider integration is not configured yet.")


def get_llm_provider() -> LLMProvider:
    providers: dict[str, LLMProvider] = {
        "mock": MockLLMProvider(),
        "placeholder": PlaceholderLLMProvider(),
    }
    return providers.get(settings.llm_provider, MockLLMProvider())

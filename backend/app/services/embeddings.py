from abc import ABC, abstractmethod
from functools import lru_cache
import hashlib
import math
import os
import re
from typing import Sequence

from backend.app.core.config import get_settings

settings = get_settings()


class EmbeddingProviderError(Exception):
    pass


class EmbeddingProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    provider_name = "mock"
    model_name = "mock-deterministic-v1"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        normalized = text.strip().lower()
        if not normalized:
            return [0.0] * settings.resolved_embedding_dimensions

        values = [0.0] * settings.resolved_embedding_dimensions
        tokens = re.findall(r"[a-z0-9]+", normalized)
        if not tokens:
            tokens = [normalized]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(settings.resolved_embedding_dimensions):
                byte_value = digest[index % len(digest)]
                values[index] += (byte_value / 127.5) - 1.0

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return [0.0] * settings.resolved_embedding_dimensions

        return [round(value / norm, 6) for value in values]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider_name = "openai"
    model_name = settings.embedding_model

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EmbeddingProviderError("OPENAI_API_KEY is not configured.")

        from openai import OpenAI

        client_kwargs = {"api_key": api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self._client = OpenAI(**client_kwargs)
        return self._client

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self._get_client().embeddings.create(
            model=settings.embedding_model,
            input=list(texts),
            dimensions=settings.resolved_embedding_dimensions,
        )
        return [list(item.embedding) for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        embeddings = self.embed_documents([text])
        if not embeddings:
            return [0.0] * settings.resolved_embedding_dimensions
        return embeddings[0]


class PlaceholderEmbeddingProvider(EmbeddingProvider):
    provider_name = "placeholder"
    model_name = "unconfigured"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingProviderError("Real embedding provider integration is not configured yet.")

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingProviderError("Real embedding provider integration is not configured yet.")


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    providers: dict[str, EmbeddingProvider] = {
        "openai": OpenAIEmbeddingProvider(),
        "mock": MockEmbeddingProvider(),
        "placeholder": PlaceholderEmbeddingProvider(),
    }
    return providers.get(settings.embedding_provider, OpenAIEmbeddingProvider())

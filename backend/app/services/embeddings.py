from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import Sequence

from backend.app.core.config import get_settings

settings = get_settings()


class EmbeddingProvider(ABC):
    provider_name: str

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    provider_name = "mock"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        normalized = text.strip().lower()
        if not normalized:
            return [0.0] * settings.embedding_dimensions

        values = [0.0] * settings.embedding_dimensions
        tokens = re.findall(r"[a-z0-9]+", normalized)
        if not tokens:
            tokens = [normalized]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(settings.embedding_dimensions):
                byte_value = digest[index % len(digest)]
                values[index] += (byte_value / 127.5) - 1.0

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return [0.0] * settings.embedding_dimensions

        return [round(value / norm, 6) for value in values]


class PlaceholderEmbeddingProvider(EmbeddingProvider):
    provider_name = "placeholder"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Real embedding provider integration is not configured yet.")

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Real embedding provider integration is not configured yet.")


def get_embedding_provider() -> EmbeddingProvider:
    providers: dict[str, EmbeddingProvider] = {
        "mock": MockEmbeddingProvider(),
        "placeholder": PlaceholderEmbeddingProvider(),
    }
    return providers.get(settings.embedding_provider, MockEmbeddingProvider())

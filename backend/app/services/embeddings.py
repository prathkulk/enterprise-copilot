from abc import ABC, abstractmethod
import hashlib
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
        normalized = text.strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(settings.embedding_dimensions):
            byte_value = digest[index % len(digest)]
            values.append(round((byte_value / 127.5) - 1.0, 6))
        return values


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

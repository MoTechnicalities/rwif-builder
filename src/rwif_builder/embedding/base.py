from __future__ import annotations

from typing import Protocol

import numpy as np

from ..config.schema import EmbeddingConfig
from .hashing import HashingActivationProvider
from .transformers import TransformersActivationProvider


class ActivationProvider(Protocol):
    def encode_text(self, text: str) -> np.ndarray: ...

    def encode_texts(self, texts: list[str]) -> np.ndarray: ...


def build_provider(config: EmbeddingConfig) -> ActivationProvider:
    provider_name = config.provider.strip().lower()
    if provider_name == "hashing":
        return HashingActivationProvider(model_id=config.model, vector_length=config.vector_length)
    if provider_name in {"transformers", "sentence-transformers"}:
        return TransformersActivationProvider(
            model_id=config.model,
            pooling=config.pooling,
            max_length=config.max_length,
            device=config.device,
        )
    raise ValueError(f"unsupported embedding provider: {config.provider}")

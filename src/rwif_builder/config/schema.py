from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceConfig:
    path: str
    type: str | None = None
    include: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChunkingConfig:
    strategy: str
    max_tokens: int
    overlap_tokens: int = 0


@dataclass(slots=True)
class EmbeddingConfig:
    provider: str
    model: str
    vector_length: int = 256
    pooling: str = "mean"
    device: str | None = None
    max_length: int = 256


@dataclass(slots=True)
class OutputConfig:
    path: str


@dataclass(slots=True)
class BuilderConfig:
    project: str
    version: str
    sources: list[SourceConfig]
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    output: OutputConfig
    metadata: dict[str, Any]
    top_k_waves: int = 128

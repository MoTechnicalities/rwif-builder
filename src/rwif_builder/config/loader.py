from __future__ import annotations

from pathlib import Path

import yaml

from .schema import BuilderConfig
from .schema import ChunkingConfig
from .schema import EmbeddingConfig
from .schema import OutputConfig
from .schema import SourceConfig


REQUIRED_KEYS = {"project", "version", "sources", "chunking", "embedding", "output"}


def load_config(path: Path) -> BuilderConfig:
    if not path.exists():
        raise SystemExit(f"config file not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("config file must contain a mapping")

    missing = sorted(REQUIRED_KEYS - payload.keys())
    if missing:
        raise SystemExit(f"config file is missing required keys: {', '.join(missing)}")

    sources = [SourceConfig(**item) for item in payload["sources"]]
    chunking = ChunkingConfig(**payload["chunking"])
    embedding_payload = dict(payload["embedding"])
    embedding_payload.setdefault("vector_length", 256)
    embedding_payload.setdefault("pooling", "mean")
    embedding_payload.setdefault("device", None)
    embedding_payload.setdefault("max_length", 256)
    embedding = EmbeddingConfig(**embedding_payload)
    output = OutputConfig(**payload["output"])
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise SystemExit("metadata must be a mapping when provided")

    return BuilderConfig(
        project=payload["project"],
        version=str(payload["version"]),
        sources=sources,
        chunking=chunking,
        embedding=embedding,
        output=output,
        metadata=metadata,
        top_k_waves=int(payload.get("top_k_waves", 128)),
    )

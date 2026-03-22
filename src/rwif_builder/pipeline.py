from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .chunking.base import chunk_document
from .config.schema import BuilderConfig
from .embedding.base import build_provider
from .ingest.filesystem import load_documents
from .manifest.models import BuilderManifest
from .manifest.models import SourceManifestEntry
from .normalize.records import ChunkRecord
from .writer.rwif_writer import estimate_background
from .writer.rwif_writer import save_semantic_memory_artifact


def build_artifact(config: BuilderConfig, *, output_override: str | None = None) -> dict[str, Any]:
    documents = load_documents(config.sources)
    chunks: list[ChunkRecord] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                max_tokens=config.chunking.max_tokens,
                overlap_tokens=config.chunking.overlap_tokens,
            )
        )
    if not chunks:
        raise ValueError("no chunks were generated from the provided sources")

    provider = build_provider(config.embedding)
    activations = provider.encode_texts([chunk.canonical_text for chunk in chunks])
    activations = np.asarray(activations, dtype=np.float64)
    if activations.ndim != 2 or activations.shape[0] != len(chunks):
        raise ValueError("embedding provider returned an invalid activation matrix")

    background = estimate_background(activations)
    chunk_counts = Counter(chunk.source_document.relative_path for chunk in chunks)
    manifest = BuilderManifest(
        manifest_version=1,
        builder_version=__version__,
        project=config.project,
        project_version=config.version,
        source_count=len(documents),
        chunk_count=len(chunks),
        vector_length=int(activations.shape[1]),
        embedding={
            "provider": config.embedding.provider,
            "model": config.embedding.model,
            "vector_length": int(activations.shape[1]),
            "pooling": config.embedding.pooling,
        },
        chunking={
            "strategy": config.chunking.strategy,
            "max_tokens": config.chunking.max_tokens,
            "overlap_tokens": config.chunking.overlap_tokens,
        },
        metadata=dict(config.metadata),
        sources=[
            SourceManifestEntry(
                relative_path=document.relative_path,
                source_type=document.source_type,
                sha256=document.sha256,
                modified_at=document.modified_at,
                chunk_count=chunk_counts[document.relative_path],
            )
            for document in documents
        ],
    )
    output_path = Path(output_override or config.output.path)
    save_semantic_memory_artifact(
        output_path,
        chunks=chunks,
        activations=activations,
        background=background,
        manifest=manifest,
        source_model=config.embedding.model,
        top_k_waves=config.top_k_waves,
    )
    return {
        "status": "built",
        "project": config.project,
        "output": str(output_path),
        "source_count": len(documents),
        "chunk_count": len(chunks),
        "vector_length": int(activations.shape[1]),
        "source_types": dict(Counter(document.source_type for document in documents)),
    }

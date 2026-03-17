from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    source_path: Path
    relative_path: str
    source_type: str
    text: str
    sha256: str
    modified_at: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    memory_id: str
    source_document: SourceDocument
    title: str
    canonical_text: str
    locator: str
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

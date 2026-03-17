from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class SourceManifestEntry:
    relative_path: str
    source_type: str
    sha256: str
    modified_at: str | None
    chunk_count: int

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "relative_path": self.relative_path,
            "source_type": self.source_type,
            "sha256": self.sha256,
            "chunk_count": self.chunk_count,
        }
        if self.modified_at is not None:
            payload["modified_at"] = self.modified_at
        return payload


@dataclass(frozen=True)
class BuilderManifest:
    manifest_version: int
    builder_version: str
    project: str
    project_version: str
    source_count: int
    chunk_count: int
    vector_length: int
    embedding: dict[str, Any]
    chunking: dict[str, Any]
    sources: list[SourceManifestEntry] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "builder_version": self.builder_version,
            "project": self.project,
            "project_version": self.project_version,
            "source_count": self.source_count,
            "chunk_count": self.chunk_count,
            "vector_length": self.vector_length,
            "embedding": dict(self.embedding),
            "chunking": dict(self.chunking),
            "sources": [entry.to_payload() for entry in self.sources],
        }

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..writer.rwif_writer import MEMORY_METADATA_KEY
from ..writer.rwif_writer import SEMANTIC_MEMORY_METADATA_KEY
from ..writer.rwif_writer import load_semantic_memory_artifact


def inspect_artifact(path: str | Path) -> dict[str, Any]:
    loaded = load_semantic_memory_artifact(path)
    library = loaded.library
    manifest = loaded.manifest
    sample_titles: list[str] = []
    sample_sources: list[str] = []
    for state in library.states[:5]:
        memory_payload = state.metadata.get(MEMORY_METADATA_KEY, {}) if isinstance(state.metadata, dict) else {}
        record_metadata = memory_payload.get("metadata", {}) if isinstance(memory_payload, dict) else {}
        semantic_payload = record_metadata.get(SEMANTIC_MEMORY_METADATA_KEY, {}) if isinstance(record_metadata, dict) else {}
        title = semantic_payload.get("title")
        source = semantic_payload.get("metadata", {}).get("relative_path") if isinstance(semantic_payload.get("metadata", {}), dict) else None
        if title:
            sample_titles.append(str(title))
        if source:
            sample_sources.append(str(source))
    return {
        "artifact": str(path),
        "format": library.metadata.get("format"),
        "semantic_memory_version": library.metadata.get("semantic_memory_version"),
        "project": manifest.get("project"),
        "project_version": manifest.get("project_version"),
        "metadata": _manifest_metadata(manifest),
        "realm_references": _realm_references(manifest),
        "record_count": len(library.states),
        "source_count": manifest.get("source_count"),
        "vector_length": manifest.get("vector_length"),
        "embedding": manifest.get("embedding", {}),
        "chunking": manifest.get("chunking", {}),
        "manifest_sources": manifest.get("sources", []),
        "sample_titles": sample_titles,
        "sample_sources": sample_sources,
    }


def _manifest_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = manifest.get("metadata", {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def _realm_references(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = _manifest_metadata(manifest)
    raw_references = metadata.get("related_realms")
    if raw_references is None:
        raw_references = metadata.get("realm_references")
    if not isinstance(raw_references, list):
        return []

    references: list[dict[str, Any]] = []
    for entry in raw_references:
        if not isinstance(entry, dict):
            continue
        realm = entry.get("realm")
        if not isinstance(realm, str) or not realm:
            continue
        references.append(dict(entry))
    return references

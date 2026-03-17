from __future__ import annotations

from pathlib import Path
from typing import Any

from .writer.rwif_writer import load_semantic_memory_artifact


def diff_artifacts(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_loaded = load_semantic_memory_artifact(left)
    right_loaded = load_semantic_memory_artifact(right)
    left_manifest = left_loaded.manifest
    right_manifest = right_loaded.manifest

    left_sources = _source_map(left_manifest)
    right_sources = _source_map(right_manifest)

    left_paths = set(left_sources)
    right_paths = set(right_sources)
    added = sorted(right_paths - left_paths)
    removed = sorted(left_paths - right_paths)
    changed = sorted(
        path
        for path in left_paths & right_paths
        if left_sources[path] != right_sources[path]
    )
    unchanged = sorted(
        path
        for path in left_paths & right_paths
        if left_sources[path] == right_sources[path]
    )

    return {
        "left": str(left),
        "right": str(right),
        "compatible_format": left_loaded.library.metadata.get("format") == right_loaded.library.metadata.get("format"),
        "project_changed": left_manifest.get("project") != right_manifest.get("project"),
        "embedding_changed": left_manifest.get("embedding") != right_manifest.get("embedding"),
        "chunking_changed": left_manifest.get("chunking") != right_manifest.get("chunking"),
        "vector_length_changed": left_manifest.get("vector_length") != right_manifest.get("vector_length"),
        "record_count_delta": int(right_manifest.get("chunk_count", 0)) - int(left_manifest.get("chunk_count", 0)),
        "source_count_delta": int(right_manifest.get("source_count", 0)) - int(left_manifest.get("source_count", 0)),
        "added_sources": added,
        "removed_sources": removed,
        "changed_sources": changed,
        "unchanged_sources": unchanged,
        "change_summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": len(unchanged),
        },
    }


def _source_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("sources", [])
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("relative_path")
        if not path:
            continue
        result[str(path)] = {
            "sha256": entry.get("sha256"),
            "source_type": entry.get("source_type"),
            "chunk_count": entry.get("chunk_count"),
        }
    return result

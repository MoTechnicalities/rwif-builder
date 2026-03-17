from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from typing import Any

from .config.schema import BuilderConfig
from .ingest.filesystem import load_documents
from .pipeline import build_artifact
from .writer.rwif_writer import load_semantic_memory_artifact


def patch_artifact(config: BuilderConfig, *, base: str | Path, output_override: str | None = None) -> dict[str, Any]:
    base_path = Path(base)
    loaded = load_semantic_memory_artifact(base_path)
    base_manifest = loaded.manifest
    current_documents = load_documents(config.sources)
    current_sources = {
        document.relative_path: {
            "sha256": document.sha256,
            "source_type": document.source_type,
        }
        for document in current_documents
    }
    base_sources = {
        str(entry.get("relative_path")): {
            "sha256": entry.get("sha256"),
            "source_type": entry.get("source_type"),
        }
        for entry in base_manifest.get("sources", [])
        if isinstance(entry, dict) and entry.get("relative_path")
    }

    current_paths = set(current_sources)
    base_paths = set(base_sources)
    added = sorted(current_paths - base_paths)
    removed = sorted(base_paths - current_paths)
    changed = sorted(
        path
        for path in current_paths & base_paths
        if current_sources[path] != base_sources[path]
    )
    unchanged = sorted(
        path
        for path in current_paths & base_paths
        if current_sources[path] == base_sources[path]
    )

    pipeline_changed = (
        base_manifest.get("embedding")
        != {
            "provider": config.embedding.provider,
            "model": config.embedding.model,
            "vector_length": config.embedding.vector_length,
            "pooling": config.embedding.pooling,
        }
        or base_manifest.get("chunking")
        != {
            "strategy": config.chunking.strategy,
            "max_tokens": config.chunking.max_tokens,
            "overlap_tokens": config.chunking.overlap_tokens,
        }
    )

    output_path = Path(output_override or config.output.path)
    if not added and not removed and not changed and not pipeline_changed:
        if output_path.resolve() != base_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            copyfile(base_path, output_path)
        return {
            "status": "no_changes",
            "base": str(base_path),
            "output": str(output_path),
            "rebuild_mode": "copy",
            "pipeline_changed": False,
            "added_sources": added,
            "removed_sources": removed,
            "changed_sources": changed,
            "unchanged_sources": unchanged,
        }

    build_payload = build_artifact(config, output_override=str(output_path))
    build_payload.update(
        {
            "status": "patched",
            "base": str(base_path),
            "rebuild_mode": "full",
            "pipeline_changed": pipeline_changed,
            "added_sources": added,
            "removed_sources": removed,
            "changed_sources": changed,
            "unchanged_sources": unchanged,
        }
    )
    return build_payload

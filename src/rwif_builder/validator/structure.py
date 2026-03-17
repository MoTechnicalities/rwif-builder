from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import BUILDER_MANIFEST_KEY
from ..writer.rwif_writer import MEMORY_METADATA_KEY
from ..writer.rwif_writer import SEMANTIC_MEMORY_METADATA_KEY
from ..writer.rwif_writer import load_semantic_memory_artifact


@dataclass(frozen=True)
class ValidationReport:
    artifact: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


def validate_artifact(path: str | Path) -> ValidationReport:
    artifact_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    try:
        loaded = load_semantic_memory_artifact(artifact_path)
    except Exception as exc:
        return ValidationReport(artifact=str(artifact_path), is_valid=False, errors=(str(exc),))

    library = loaded.library
    manifest = loaded.manifest
    stats["record_count"] = len(library.states)
    stats["has_background"] = "background" in library.metadata

    if library.metadata.get("format") != "rwif_semantic_memory":
        errors.append("library metadata format must be 'rwif_semantic_memory'")
    if int(library.metadata.get("semantic_memory_version", 0)) != 1:
        errors.append("semantic_memory_version must be 1")
    if BUILDER_MANIFEST_KEY not in library.metadata:
        errors.append("library metadata is missing rwif_builder_manifest")
    if not isinstance(manifest, dict):
        errors.append("builder manifest must be a mapping")
    else:
        if int(manifest.get("manifest_version", 0)) != 1:
            errors.append("builder manifest version must be 1")
        if int(manifest.get("chunk_count", -1)) != len(library.states):
            errors.append("builder manifest chunk_count does not match state count")
        stats["project"] = manifest.get("project")
        stats["vector_length"] = manifest.get("vector_length")

    expected_vector_length = None
    background = library.metadata.get("background")
    if isinstance(background, list) and background:
        expected_vector_length = len(background)

    for index, state in enumerate(library.states):
        if expected_vector_length is None:
            expected_vector_length = state.vector_length
        if state.vector_length != expected_vector_length:
            errors.append(f"state {index} has vector_length {state.vector_length}, expected {expected_vector_length}")
        if state.top_k <= 0:
            errors.append(f"state {index} has non-positive top_k")
        if len(state.units) == 0:
            errors.append(f"state {index} has no wave units")
        seen_indices: set[int] = set()
        for unit in state.units:
            if unit.frequency_index < 0 or unit.frequency_index >= state.vector_length:
                errors.append(f"state {index} has out-of-range frequency index {unit.frequency_index}")
            if unit.frequency_index in seen_indices:
                errors.append(f"state {index} has duplicate frequency index {unit.frequency_index}")
            seen_indices.add(unit.frequency_index)
        memory_payload = state.metadata.get(MEMORY_METADATA_KEY, {}) if isinstance(state.metadata, dict) else {}
        if not isinstance(memory_payload, dict):
            errors.append(f"state {index} is missing rwif_memory_store metadata")
            continue
        record_metadata = memory_payload.get("metadata", {})
        if not isinstance(record_metadata, dict):
            errors.append(f"state {index} record metadata must be a mapping")
            continue
        semantic_payload = record_metadata.get(SEMANTIC_MEMORY_METADATA_KEY)
        if not isinstance(semantic_payload, dict):
            errors.append(f"state {index} is missing semantic memory payload")
            continue
        for key in ("memory_id", "title", "canonical_text"):
            if not semantic_payload.get(key):
                errors.append(f"state {index} semantic payload is missing '{key}'")
        if semantic_payload.get("kind") != "document_chunk":
            warnings.append(f"state {index} kind is {semantic_payload.get('kind')!r}, expected 'document_chunk'")

    return ValidationReport(
        artifact=str(artifact_path),
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
    )

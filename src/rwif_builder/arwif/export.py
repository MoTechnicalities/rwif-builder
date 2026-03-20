from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..writer.rwif_writer import load_wave_library
from .validation import validate_arwif_artifact

_LIBRARY_SPEC_KEYS = {
    "title",
    "description",
    "sample_rate_hz",
    "default_duration_seconds",
    "default_phase_radians",
    "default_attack_ms",
    "default_release_ms",
    "normalize",
}

_LIBRARY_INTERNAL_KEYS = {
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
}

_STATE_SPEC_KEYS = {
    "duration_seconds",
    "phase_radians",
    "gain",
    "attack_ms",
    "release_ms",
}


def export_arwif_artifact(
    artifact: str | Path,
    output: str | Path,
    *,
    format: str | None = None,
    allow_legacy: bool = False,
) -> dict[str, Any]:
    artifact_path = Path(artifact)
    output_path = Path(output)
    library = load_wave_library(artifact_path)
    validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
    export_format = _resolve_export_format(output_path, format)
    document = _artifact_to_spec(library.metadata, library.states)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    else:
        output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    return {
        "artifact": str(artifact_path),
        "output": str(output_path),
        "format": export_format,
        "is_valid": validation_report.is_valid,
        "warnings": list(validation_report.warnings),
        "errors": list(validation_report.errors),
        "legacy_mode": validation_report.stats.get("legacy_mode", False),
        "state_count": len(library.states),
        "oscillator_count": sum(len(state.units) for state in library.states),
    }


def _resolve_export_format(output_path: Path, explicit_format: str | None) -> str:
    if explicit_format is not None:
        normalized = explicit_format.lower()
        if normalized not in {"yaml", "json"}:
            raise ValueError("format must be yaml or json")
        return normalized
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError("could not infer export format from output path; use --format yaml or --format json")


def _artifact_to_spec(library_metadata: dict[str, Any], states: tuple[Any, ...]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    metadata_extras = {
        key: value
        for key, value in library_metadata.items()
        if key not in _LIBRARY_SPEC_KEYS and key not in _LIBRARY_INTERNAL_KEYS
    }
    for key in (
        "title",
        "description",
        "sample_rate_hz",
        "default_duration_seconds",
        "default_phase_radians",
        "default_attack_ms",
        "default_release_ms",
        "normalize",
    ):
        if key in library_metadata:
            document[key] = library_metadata[key]
    if metadata_extras:
        document["metadata"] = metadata_extras
    document["states"] = [_state_to_spec(state) for state in states]
    return document


def _state_to_spec(state: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    if state.label is not None:
        entry["label"] = state.label

    state_metadata = dict(state.metadata or {})
    state_metadata_extras = {key: value for key, value in state_metadata.items() if key not in _STATE_SPEC_KEYS}

    for key in ("duration_seconds", "phase_radians", "gain", "attack_ms", "release_ms"):
        if key in state_metadata:
            entry[key] = state_metadata[key]

    if state.vector_length:
        entry["vector_length"] = state.vector_length
    if state.top_k:
        entry["top_k"] = state.top_k
    if state.centered_norm:
        entry["centered_norm"] = state.centered_norm
    if state.original_norm:
        entry["original_norm"] = state.original_norm
    if state_metadata_extras:
        entry["metadata"] = state_metadata_extras

    entry["oscillators"] = [{"hz": unit.frequency_index, "amplitude": unit.amplitude} for unit in state.units]
    return entry
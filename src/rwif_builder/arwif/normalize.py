from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..writer.rwif_writer import load_wave_library
from .importing import import_arwif_artifact
from .validation import ARWIF_FORMAT
from .validation import ARWIF_FREQUENCY_UNIT
from .validation import ARWIF_PLAYBACK_MODEL
from .validation import ARWIF_VERSION
from .validation import DEFAULT_ATTACK_MS
from .validation import DEFAULT_DURATION_SECONDS
from .validation import DEFAULT_RELEASE_MS
from .validation import DEFAULT_SAMPLE_RATE_HZ
from .validation import validate_arwif_artifact
from .validation import validate_arwif_spec_document

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


def normalize_arwif_artifact(
    artifact: str | Path,
    spec_output: str | Path,
    *,
    output: str | Path | None = None,
    format: str | None = None,
) -> dict[str, Any]:
    artifact_path = Path(artifact)
    spec_output_path = Path(spec_output)
    output_path = Path(output) if output is not None else None

    library = load_wave_library(artifact_path)
    source_report = validate_arwif_artifact(artifact_path, allow_legacy=True)
    if not source_report.is_valid:
        raise ValueError("source artifact is not valid even in legacy-compatible mode")

    export_format = _resolve_export_format(spec_output_path, format)
    document, normalization = _artifact_to_normalized_spec(library.metadata, library.states)
    spec_report = validate_arwif_spec_document(document, source=str(artifact_path))
    if not spec_report.is_valid:
        raise ValueError("generated normalized spec failed validation")

    _write_spec_document(spec_output_path, document, export_format)

    payload: dict[str, Any] = {
        "artifact": str(artifact_path),
        "spec_output": str(spec_output_path),
        "format": export_format,
        "legacy_mode": source_report.stats.get("legacy_mode", False),
        "source_is_valid": source_report.is_valid,
        "source_errors": list(source_report.errors),
        "source_warnings": list(source_report.warnings),
        "normalized_spec_is_valid": spec_report.is_valid,
        "normalized_spec_errors": list(spec_report.errors),
        "normalized_spec_warnings": list(spec_report.warnings),
        "normalized_state_count": len(library.states),
        "normalized_oscillator_count": sum(len(state.units) for state in library.states),
        "injected_defaults": normalization["injected_defaults"],
        "preserved_metadata_keys": normalization["preserved_metadata_keys"],
        "normalized": True,
    }

    if output_path is not None:
        import_payload = import_arwif_artifact(spec_output_path, output_path)
        payload.update(
            {
                "output": str(output_path),
                "output_is_valid": import_payload["is_valid"],
                "output_validation_errors": import_payload["validation_errors"],
                "output_validation_warnings": import_payload["validation_warnings"],
                "output_validation_stats": import_payload["validation_stats"],
            }
        )

    return payload


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


def _write_spec_document(output_path: Path, document: dict[str, Any], export_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _artifact_to_normalized_spec(library_metadata: dict[str, Any], states: tuple[Any, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = dict(library_metadata)
    injected_defaults: list[str] = []

    sample_rate_hz = metadata.get("sample_rate_hz")
    if not isinstance(sample_rate_hz, int) or sample_rate_hz <= 0:
        sample_rate_hz = DEFAULT_SAMPLE_RATE_HZ
        injected_defaults.append("sample_rate_hz")

    default_duration_seconds = metadata.get("default_duration_seconds")
    if not isinstance(default_duration_seconds, (int, float)) or float(default_duration_seconds) <= 0.0:
        default_duration_seconds = DEFAULT_DURATION_SECONDS
        injected_defaults.append("default_duration_seconds")

    default_phase_radians = metadata.get("default_phase_radians")
    if not isinstance(default_phase_radians, (int, float)):
        default_phase_radians = 0.0
        injected_defaults.append("default_phase_radians")

    default_attack_ms = metadata.get("default_attack_ms")
    if not isinstance(default_attack_ms, (int, float)) or float(default_attack_ms) < 0.0:
        default_attack_ms = DEFAULT_ATTACK_MS
        injected_defaults.append("default_attack_ms")

    default_release_ms = metadata.get("default_release_ms")
    if not isinstance(default_release_ms, (int, float)) or float(default_release_ms) < 0.0:
        default_release_ms = DEFAULT_RELEASE_MS
        injected_defaults.append("default_release_ms")

    normalize = metadata.get("normalize")
    if not isinstance(normalize, bool):
        normalize = True
        injected_defaults.append("normalize")

    normalized_metadata = {
        "format": ARWIF_FORMAT,
        "arwif_version": ARWIF_VERSION,
        "frequency_unit": ARWIF_FREQUENCY_UNIT,
        "playback_model": ARWIF_PLAYBACK_MODEL,
        "sample_rate_hz": sample_rate_hz,
        "default_duration_seconds": float(default_duration_seconds),
        "default_phase_radians": float(default_phase_radians),
        "default_attack_ms": float(default_attack_ms),
        "default_release_ms": float(default_release_ms),
        "normalize": normalize,
    }

    for key in ("title", "description"):
        if key in metadata and isinstance(metadata[key], str):
            normalized_metadata[key] = metadata[key]

    metadata_extras = {
        key: value
        for key, value in metadata.items()
        if key not in _LIBRARY_SPEC_KEYS and key not in _LIBRARY_INTERNAL_KEYS
    }

    document: dict[str, Any] = {}
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
        if key in normalized_metadata:
            document[key] = normalized_metadata[key]

    if metadata_extras:
        document["metadata"] = metadata_extras

    document["states"] = [_state_to_spec(state) for state in states]
    return document, {
        "injected_defaults": injected_defaults,
        "preserved_metadata_keys": sorted(metadata_extras.keys()),
    }


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
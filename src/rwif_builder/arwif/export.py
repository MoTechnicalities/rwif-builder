from __future__ import annotations

import json
from pathlib import Path
import math
from typing import Any

import yaml

from ..writer.rwif_writer import load_wave_library
from .validation import validate_arwif_artifact

_LIBRARY_SPEC_KEYS = {
    "title",
    "description",
    "channel_layout",
    "listener_anchor",
    "reference_frame",
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
    "source_id",
    "source_groups",
    "channel_gains",
    "position",
    "trajectory",
    "orientation",
    "spread",
    "distance_model",
    "attack_ms",
    "release_ms",
}


def _channel_gains_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _spatial_vector_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        component = value.get(axis)
        if not isinstance(component, (int, float)) or not math.isfinite(float(component)):
            return {}
        result[axis] = float(component)
    return result


def _trajectory_mapping(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    trajectory: list[dict[str, Any]] = []
    for keyframe in value:
        if not isinstance(keyframe, dict):
            return []
        position = _spatial_vector_mapping(keyframe.get("position"))
        offset_seconds = keyframe.get("offset_seconds")
        if not position:
            return []
        if not isinstance(offset_seconds, (int, float)) or not math.isfinite(float(offset_seconds)) or float(offset_seconds) < 0.0:
            return []
        trajectory.append(
            {
                "offset_seconds": float(offset_seconds),
                "position": position,
            }
        )
    return trajectory


def _spread_value(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) >= 0.0:
        return float(value)
    return None


def _distance_model_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


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
        "channel_layout",
        "listener_anchor",
        "reference_frame",
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
    if "source_id" in state_metadata:
        entry["source_id"] = state_metadata["source_id"]
    if "source_groups" in state_metadata and isinstance(state_metadata["source_groups"], list):
        entry["source_groups"] = list(state_metadata["source_groups"])
    if "channel_gains" in state_metadata:
        entry["channel_gains"] = _channel_gains_mapping(state_metadata.get("channel_gains"))
    if "position" in state_metadata:
        entry["position"] = _spatial_vector_mapping(state_metadata.get("position"))
    if "trajectory" in state_metadata:
        entry["trajectory"] = _trajectory_mapping(state_metadata.get("trajectory"))
    if "orientation" in state_metadata:
        entry["orientation"] = _spatial_vector_mapping(state_metadata.get("orientation"))
    spread = _spread_value(state_metadata.get("spread"))
    if spread is not None:
        entry["spread"] = spread
    distance_model = _distance_model_value(state_metadata.get("distance_model"))
    if distance_model is not None:
        entry["distance_model"] = distance_model

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
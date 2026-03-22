from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import AtomicWaveUnit
from ..writer.rwif_writer import WaveLibrary
from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import save_wave_library
from .validation import ARWIF_FORMAT
from .validation import ARWIF_FREQUENCY_UNIT
from .validation import ARWIF_PLAYBACK_MODEL
from .validation import ARWIF_REFERENCE_FRAMES
from .validation import ARWIF_VERSION
from .validation import CHANNEL_LAYOUT_CHANNELS
from .validation import DEFAULT_ATTACK_MS
from .validation import DEFAULT_DURATION_SECONDS
from .validation import DEFAULT_RELEASE_MS
from .validation import DEFAULT_SAMPLE_RATE_HZ
from .validation import OBJECT_DISTANCE_MODELS
from .validation import ROOM_DIMENSION_KEYS
from .validation import ROOM_SURFACE_PROFILES
from .validation import SPATIAL_VECTOR_AXES
from .validation import validate_arwif_artifact
from .validation import validate_arwif_spec

_LIBRARY_OVERRIDE_KEYS = {
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
    "sample_rate_hz",
    "default_duration_seconds",
    "normalize",
    "default_phase_radians",
    "default_attack_ms",
    "default_release_ms",
    "channel_layout",
    "listener_anchor",
    "reference_frame",
    "room",
}


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    return dict(value)


def _require_sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return list(value)


def _require_finite_number(value: Any, context: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{context} must be a finite number")
    return float(value)


def _require_positive_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{context} must be a positive integer")
    return int(value)


def _require_non_negative_number(value: Any, context: str) -> float:
    number = _require_finite_number(value, context)
    if number < 0.0:
        raise ValueError(f"{context} must be non-negative")
    return number


def _require_positive_number(value: Any, context: str) -> float:
    number = _require_finite_number(value, context)
    if number <= 0.0:
        raise ValueError(f"{context} must be positive")
    return number


def _optional_mapping(value: Any, context: str) -> dict[str, Any]:
    if value is None:
        return {}
    return _require_mapping(value, context)


def _require_spatial_vector(value: Any, context: str) -> dict[str, float]:
    mapping = _require_mapping(value, context)
    return {
        axis: _require_finite_number(mapping.get(axis), f"{context}.{axis}")
        for axis in SPATIAL_VECTOR_AXES
    }


def _require_trajectory(value: Any, context: str, *, max_offset_seconds: float | None = None) -> list[dict[str, Any]]:
    keyframes = _require_sequence(value, context)
    if not keyframes:
        raise ValueError(f"{context} must contain at least one keyframe")

    trajectory: list[dict[str, Any]] = []
    previous_offset: float | None = None
    for index, keyframe in enumerate(keyframes):
        keyframe_mapping = _require_mapping(keyframe, f"{context}[{index}]")
        offset_seconds = _require_non_negative_number(
            keyframe_mapping.get("offset_seconds"),
            f"{context}[{index}].offset_seconds",
        )
        if max_offset_seconds is not None and offset_seconds > max_offset_seconds:
            raise ValueError(f"{context}[{index}].offset_seconds must not exceed state duration {max_offset_seconds}")
        if previous_offset is not None and offset_seconds < previous_offset:
            raise ValueError(f"{context} must be sorted by non-decreasing offset_seconds")
        previous_offset = offset_seconds
        trajectory.append(
            {
                "offset_seconds": offset_seconds,
                "position": _require_spatial_vector(keyframe_mapping.get("position"), f"{context}[{index}].position"),
            }
        )
    return trajectory


def _require_room(value: Any, context: str) -> dict[str, Any]:
    room_mapping = _require_mapping(value, context)
    room: dict[str, Any] = {}

    if "dimensions" in room_mapping:
        dimensions_mapping = _require_mapping(room_mapping.get("dimensions"), f"{context}.dimensions")
        room["dimensions"] = {
            key: _require_positive_number(dimensions_mapping.get(key), f"{context}.dimensions.{key}")
            for key in ROOM_DIMENSION_KEYS
        }

    if "surface_profile" in room_mapping:
        surface_profile = room_mapping.get("surface_profile")
        if not isinstance(surface_profile, str) or surface_profile not in ROOM_SURFACE_PROFILES:
            raise ValueError(f"{context}.surface_profile must be one of: " + ", ".join(ROOM_SURFACE_PROFILES))
        room["surface_profile"] = surface_profile

    if "listening_zones" in room_mapping:
        listening_zones_document = _require_sequence(room_mapping.get("listening_zones"), f"{context}.listening_zones")
        listening_zones: list[dict[str, Any]] = []
        for index, zone_document in enumerate(listening_zones_document):
            zone_mapping = _require_mapping(zone_document, f"{context}.listening_zones[{index}]")
            zone_id = zone_mapping.get("zone_id")
            if not isinstance(zone_id, str) or not zone_id:
                raise ValueError(f"{context}.listening_zones[{index}].zone_id must be a non-empty string")
            zone_entry = {
                "zone_id": zone_id,
                "anchor": _require_spatial_vector(zone_mapping.get("anchor"), f"{context}.listening_zones[{index}].anchor"),
                "radius_m": _require_positive_number(zone_mapping.get("radius_m"), f"{context}.listening_zones[{index}].radius_m"),
            }
            if "intent" in zone_mapping:
                intent = zone_mapping.get("intent")
                if not isinstance(intent, str) or not intent:
                    raise ValueError(f"{context}.listening_zones[{index}].intent must be a non-empty string")
                zone_entry["intent"] = intent
            listening_zones.append(zone_entry)
        room["listening_zones"] = listening_zones

    return room


def _library_metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        key: value
        for key, value in _optional_mapping(document.get("metadata"), "metadata").items()
        if key not in _LIBRARY_OVERRIDE_KEYS
    }

    sample_rate_hz = _require_positive_int(
        document.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ),
        "sample_rate_hz",
    )
    default_duration_seconds = _require_finite_number(
        document.get("default_duration_seconds", DEFAULT_DURATION_SECONDS),
        "default_duration_seconds",
    )
    if default_duration_seconds <= 0.0:
        raise ValueError("default_duration_seconds must be positive")

    default_phase_radians = _require_finite_number(
        document.get("default_phase_radians", 0.0),
        "default_phase_radians",
    )
    default_attack_ms = _require_non_negative_number(
        document.get("default_attack_ms", DEFAULT_ATTACK_MS),
        "default_attack_ms",
    )
    default_release_ms = _require_non_negative_number(
        document.get("default_release_ms", DEFAULT_RELEASE_MS),
        "default_release_ms",
    )

    normalize = document.get("normalize", True)
    if not isinstance(normalize, bool):
        raise ValueError("normalize must be a boolean")

    for optional_key in ("title", "description"):
        if optional_key in document:
            metadata[optional_key] = document[optional_key]

    channel_layout = document.get("channel_layout")
    if channel_layout is not None:
        if not isinstance(channel_layout, str) or channel_layout not in CHANNEL_LAYOUT_CHANNELS:
            raise ValueError("channel_layout must be one of: " + ", ".join(sorted(CHANNEL_LAYOUT_CHANNELS)))
        metadata["channel_layout"] = channel_layout

    if "listener_anchor" in document:
        metadata["listener_anchor"] = _require_spatial_vector(document["listener_anchor"], "listener_anchor")

    if "reference_frame" in document:
        reference_frame = document["reference_frame"]
        if not isinstance(reference_frame, str) or reference_frame not in ARWIF_REFERENCE_FRAMES:
            raise ValueError("reference_frame must be one of: " + ", ".join(ARWIF_REFERENCE_FRAMES))
        metadata["reference_frame"] = reference_frame

    if "room" in document:
        metadata["room"] = _require_room(document["room"], "room")

    metadata.update(
        {
            "format": ARWIF_FORMAT,
            "arwif_version": ARWIF_VERSION,
            "frequency_unit": ARWIF_FREQUENCY_UNIT,
            "playback_model": ARWIF_PLAYBACK_MODEL,
            "sample_rate_hz": sample_rate_hz,
            "default_duration_seconds": default_duration_seconds,
            "default_phase_radians": default_phase_radians,
            "default_attack_ms": default_attack_ms,
            "default_release_ms": default_release_ms,
            "normalize": normalize,
        }
    )
    return metadata


def _state_metadata(state_document: dict[str, Any]) -> dict[str, Any]:
    metadata = _optional_mapping(state_document.get("metadata"), "state metadata")

    if "duration_seconds" in state_document:
        duration_seconds = _require_finite_number(state_document["duration_seconds"], "state duration_seconds")
        if duration_seconds <= 0.0:
            raise ValueError("state duration_seconds must be positive")
        metadata["duration_seconds"] = duration_seconds
    if "phase_radians" in state_document:
        metadata["phase_radians"] = _require_finite_number(state_document["phase_radians"], "state phase_radians")
    if "gain" in state_document:
        metadata["gain"] = _require_finite_number(state_document["gain"], "state gain")
    if "source_id" in state_document:
        source_id = state_document["source_id"]
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("state source_id must be a non-empty string")
        metadata["source_id"] = source_id
    if "source_groups" in state_document:
        source_groups_document = _require_sequence(state_document["source_groups"], "state source_groups")
        source_groups: list[str] = []
        for group_index, group_name in enumerate(source_groups_document):
            if not isinstance(group_name, str) or not group_name:
                raise ValueError(f"state source_groups[{group_index}] must be a non-empty string")
            source_groups.append(group_name)
        metadata["source_groups"] = source_groups
    if "channel_gains" in state_document:
        channel_gains_document = _require_mapping(state_document["channel_gains"], "state channel_gains")
        channel_gains: dict[str, float] = {}
        for channel_name, channel_gain in channel_gains_document.items():
            if not isinstance(channel_name, str) or not channel_name:
                raise ValueError("state channel_gains keys must be non-empty strings")
            channel_gains[channel_name] = _require_finite_number(channel_gain, f"state channel_gains[{channel_name!r}]")
        metadata["channel_gains"] = channel_gains
    if "position" in state_document:
        metadata["position"] = _require_spatial_vector(state_document["position"], "state position")
    if "trajectory" in state_document:
        state_duration_seconds = None
        if "duration_seconds" in state_document:
            state_duration_seconds = _require_finite_number(state_document["duration_seconds"], "state duration_seconds")
            if state_duration_seconds <= 0.0:
                raise ValueError("state duration_seconds must be positive")
        metadata["trajectory"] = _require_trajectory(
            state_document["trajectory"],
            "state trajectory",
            max_offset_seconds=state_duration_seconds,
        )
    if "orientation" in state_document:
        metadata["orientation"] = _require_spatial_vector(state_document["orientation"], "state orientation")
    if "spread" in state_document:
        metadata["spread"] = _require_non_negative_number(state_document["spread"], "state spread")
    if "distance_model" in state_document:
        distance_model = state_document["distance_model"]
        if not isinstance(distance_model, str) or distance_model not in OBJECT_DISTANCE_MODELS:
            raise ValueError("state distance_model must be one of: " + ", ".join(OBJECT_DISTANCE_MODELS))
        metadata["distance_model"] = distance_model
    if "attack_ms" in state_document:
        metadata["attack_ms"] = _require_non_negative_number(state_document["attack_ms"], "state attack_ms")
    if "release_ms" in state_document:
        metadata["release_ms"] = _require_non_negative_number(state_document["release_ms"], "state release_ms")

    return metadata


def _build_state(state_document: dict[str, Any], index: int) -> WaveState:
    oscillators = _require_sequence(state_document.get("oscillators"), f"states[{index}].oscillators")
    if not oscillators:
        raise ValueError(f"states[{index}].oscillators must contain at least one oscillator")

    units: list[AtomicWaveUnit] = []
    max_frequency_hz = 1
    for oscillator_index, oscillator in enumerate(oscillators):
        entry = _require_mapping(oscillator, f"states[{index}].oscillators[{oscillator_index}]")
        frequency_hz = _require_positive_int(entry.get("hz"), f"states[{index}].oscillators[{oscillator_index}].hz")
        amplitude = _require_finite_number(
            entry.get("amplitude"),
            f"states[{index}].oscillators[{oscillator_index}].amplitude",
        )
        units.append(AtomicWaveUnit(frequency_index=frequency_hz, amplitude=amplitude))
        max_frequency_hz = max(max_frequency_hz, frequency_hz)

    vector_length_value = state_document.get("vector_length", max_frequency_hz + 1)
    vector_length = _require_positive_int(vector_length_value, f"states[{index}].vector_length")

    label = state_document.get("label")
    if label is not None and not isinstance(label, str):
        raise ValueError(f"states[{index}].label must be a string")

    top_k = state_document.get("top_k", len(units))
    top_k_value = _require_positive_int(top_k, f"states[{index}].top_k")
    centered_norm = _require_finite_number(state_document.get("centered_norm", 0.0), f"states[{index}].centered_norm")
    original_norm = _require_finite_number(state_document.get("original_norm", 0.0), f"states[{index}].original_norm")

    return WaveState(
        vector_length=vector_length,
        units=tuple(units),
        label=label,
        centered_norm=centered_norm,
        original_norm=original_norm,
        top_k=top_k_value,
        metadata=_state_metadata(state_document),
    )


def build_arwif_artifact(spec: str | Path, output: str | Path) -> dict[str, Any]:
    spec_path = Path(spec)
    output_path = Path(output)
    spec_report = validate_arwif_spec(spec_path)
    if not spec_report.is_valid or spec_report.normalized_document is None:
        raise ValueError("; ".join(spec_report.errors) or "ARWIF spec validation failed")

    document = spec_report.normalized_document
    states_document = _require_sequence(document.get("states"), "states")
    if not states_document:
        raise ValueError("states must contain at least one state")

    states = tuple(_build_state(_require_mapping(item, f"states[{index}]"), index) for index, item in enumerate(states_document))
    library = WaveLibrary(states=states, metadata=_library_metadata(document))
    save_wave_library(output_path, library)

    validation_report = validate_arwif_artifact(output_path)
    oscillator_count = sum(len(state.units) for state in states)
    return {
        "artifact": str(output_path),
        "spec": str(spec_path),
        "state_count": len(states),
        "oscillator_count": oscillator_count,
        "spec_is_valid": spec_report.is_valid,
        "spec_validation_errors": list(spec_report.errors),
        "spec_validation_warnings": list(spec_report.warnings),
        "spec_validation_stats": dict(spec_report.stats),
        "is_valid": validation_report.is_valid,
        "validation_errors": list(validation_report.errors),
        "validation_warnings": list(validation_report.warnings),
        "validation_stats": dict(validation_report.stats),
    }
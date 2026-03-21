from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import AtomicWaveUnit
from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import load_wave_library
from .validation import CHANNEL_LAYOUT_CHANNELS
from .validation import validate_arwif_artifact

_METADATA_KEYS = (
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
    "channel_layout",
    "listener_anchor",
    "sample_rate_hz",
    "default_duration_seconds",
    "default_attack_ms",
    "default_release_ms",
    "default_phase_radians",
    "normalize",
    "title",
    "description",
)


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


def _spread_value(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) >= 0.0:
        return float(value)
    return None


def _distance_model_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def diff_arwif_artifacts(left: str | Path, right: str | Path, *, allow_legacy: bool = False) -> dict[str, Any]:
    left_path = Path(left)
    right_path = Path(right)

    left_library = load_wave_library(left_path)
    right_library = load_wave_library(right_path)
    left_report = validate_arwif_artifact(left_path, allow_legacy=allow_legacy)
    right_report = validate_arwif_artifact(right_path, allow_legacy=allow_legacy)

    left_metadata = dict(left_library.metadata)
    right_metadata = dict(right_library.metadata)
    metadata_changes = {
        key: {"left": left_metadata.get(key), "right": right_metadata.get(key)}
        for key in _METADATA_KEYS
        if left_metadata.get(key) != right_metadata.get(key)
    }

    left_states = _state_map(left_library.states)
    right_states = _state_map(right_library.states)
    left_keys = set(left_states)
    right_keys = set(right_states)

    added_states = sorted(right_keys - left_keys)
    removed_states = sorted(left_keys - right_keys)
    changed_states = sorted(
        key for key in left_keys & right_keys if _state_signature(left_states[key]) != _state_signature(right_states[key])
    )
    unchanged_states = sorted(
        key for key in left_keys & right_keys if _state_signature(left_states[key]) == _state_signature(right_states[key])
    )

    state_changes = {
        key: _describe_state_change(left_states[key], right_states[key])
        for key in changed_states
    }

    left_oscillator_count = sum(len(state.units) for state in left_library.states)
    right_oscillator_count = sum(len(state.units) for state in right_library.states)

    return {
        "left": str(left_path),
        "right": str(right_path),
        "compatible_format": left_metadata.get("format") == right_metadata.get("format"),
        "left_valid": left_report.is_valid,
        "right_valid": right_report.is_valid,
        "left_legacy_mode": left_report.stats.get("legacy_mode", False),
        "right_legacy_mode": right_report.stats.get("legacy_mode", False),
        "metadata_changes": metadata_changes,
        "left_spatial_summary": _spatial_summary(left_metadata, left_library.states),
        "right_spatial_summary": _spatial_summary(right_metadata, right_library.states),
        "spatial_changes": _spatial_changes(left_metadata, left_library.states, right_metadata, right_library.states),
        "state_count_delta": len(right_library.states) - len(left_library.states),
        "oscillator_count_delta": right_oscillator_count - left_oscillator_count,
        "added_states": added_states,
        "removed_states": removed_states,
        "changed_states": changed_states,
        "unchanged_states": unchanged_states,
        "state_changes": state_changes,
        "change_summary": {
            "metadata_fields_changed": len(metadata_changes),
            "added_states": len(added_states),
            "removed_states": len(removed_states),
            "changed_states": len(changed_states),
            "unchanged_states": len(unchanged_states),
        },
    }


def _state_map(states: tuple[WaveState, ...]) -> dict[str, WaveState]:
    result: dict[str, WaveState] = {}
    for index, state in enumerate(states):
        key = str(state.label) if state.label else f"state:{index}"
        if key in result:
            key = f"{key}#{index}"
        result[key] = state
    return result


def _state_signature(state: WaveState) -> dict[str, Any]:
    metadata = dict(state.metadata or {})
    return {
        "label": state.label,
        "vector_length": state.vector_length,
        "top_k": state.top_k,
        "centered_norm": state.centered_norm,
        "original_norm": state.original_norm,
        "metadata": metadata,
        "units": _serialize_units(state.units),
    }


def _serialize_units(units: tuple[AtomicWaveUnit, ...]) -> list[dict[str, Any]]:
    return [{"hz": unit.frequency_index, "amplitude": unit.amplitude} for unit in units]


def _describe_state_change(left: WaveState, right: WaveState) -> dict[str, Any]:
    left_metadata = dict(left.metadata or {})
    right_metadata = dict(right.metadata or {})
    metadata_changes = {
        key: {"left": left_metadata.get(key), "right": right_metadata.get(key)}
        for key in sorted(set(left_metadata) | set(right_metadata))
        if left_metadata.get(key) != right_metadata.get(key)
    }
    return {
        "left_oscillator_count": len(left.units),
        "right_oscillator_count": len(right.units),
        "left_max_frequency_hz": max((unit.frequency_index for unit in left.units), default=None),
        "right_max_frequency_hz": max((unit.frequency_index for unit in right.units), default=None),
        "metadata_changes": metadata_changes,
        "left_units": _serialize_units(left.units),
        "right_units": _serialize_units(right.units),
    }


def _spatial_summary(metadata: dict[str, Any], states: tuple[WaveState, ...]) -> dict[str, Any]:
    channel_layout = metadata.get("channel_layout")
    declared_channels = list(CHANNEL_LAYOUT_CHANNELS.get(channel_layout, ())) if isinstance(channel_layout, str) else []
    listener_anchor = _spatial_vector_mapping(metadata.get("listener_anchor"))
    active_channels = sorted(
        {
            channel_name
            for state in states
            for channel_name, gain in _channel_gains_mapping(dict(state.metadata or {}).get("channel_gains")).items()
            if float(gain) != 0.0
        }
    )
    states_with_channel_gains = sum(
        1 for state in states if _channel_gains_mapping(dict(state.metadata or {}).get("channel_gains"))
    )
    positioned_states = sum(1 for state in states if _spatial_vector_mapping(dict(state.metadata or {}).get("position")))
    states_with_orientation = sum(
        1 for state in states if _spatial_vector_mapping(dict(state.metadata or {}).get("orientation"))
    )
    states_with_spread = sum(1 for state in states if _spread_value(dict(state.metadata or {}).get("spread")) is not None)
    distance_models = sorted(
        {
            str(distance_model)
            for state in states
            for distance_model in [_distance_model_value(dict(state.metadata or {}).get("distance_model"))]
            if distance_model is not None
        }
    )
    return {
        "channel_layout": channel_layout,
        "declared_channels": declared_channels,
        "listener_anchor": listener_anchor,
        "active_channels": active_channels,
        "states_with_channel_gains": states_with_channel_gains,
        "positioned_states": positioned_states,
        "states_with_orientation": states_with_orientation,
        "states_with_spread": states_with_spread,
        "distance_models": distance_models,
    }


def _spatial_changes(
    left_metadata: dict[str, Any],
    left_states: tuple[WaveState, ...],
    right_metadata: dict[str, Any],
    right_states: tuple[WaveState, ...],
) -> dict[str, Any]:
    left_summary = _spatial_summary(left_metadata, left_states)
    right_summary = _spatial_summary(right_metadata, right_states)
    return {
        "listener_anchor_changed": left_summary["listener_anchor"] != right_summary["listener_anchor"],
        "channel_layout_changed": left_summary["channel_layout"] != right_summary["channel_layout"],
        "active_channels_changed": left_summary["active_channels"] != right_summary["active_channels"],
        "states_with_channel_gains_delta": (
            right_summary["states_with_channel_gains"] - left_summary["states_with_channel_gains"]
        ),
        "positioned_states_delta": right_summary["positioned_states"] - left_summary["positioned_states"],
        "states_with_orientation_delta": (
            right_summary["states_with_orientation"] - left_summary["states_with_orientation"]
        ),
        "states_with_spread_delta": right_summary["states_with_spread"] - left_summary["states_with_spread"],
        "distance_models_changed": left_summary["distance_models"] != right_summary["distance_models"],
    }
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import load_wave_library
from .validation import CHANNEL_LAYOUT_CHANNELS
from .validation import validate_arwif_artifact


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


def _source_groups_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [group_name for group_name in value if isinstance(group_name, str) and group_name]


def inspect_arwif_artifact(path: str | Path, *, allow_legacy: bool = False) -> dict[str, Any]:
    artifact_path = Path(path)
    library = load_wave_library(artifact_path)
    validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
    metadata = dict(library.metadata)

    state_summaries: list[dict[str, Any]] = []
    oscillator_count = 0
    max_frequency_hz = 0
    labels: list[str] = []

    for index, state in enumerate(library.states):
        state_metadata = dict(state.metadata or {})
        frequencies = [int(unit.frequency_index) for unit in state.units]
        amplitudes = [float(unit.amplitude) for unit in state.units]
        oscillator_count += len(frequencies)
        if frequencies:
            max_frequency_hz = max(max_frequency_hz, max(frequencies))
        if state.label:
            labels.append(str(state.label))
        state_summaries.append(
            {
                "index": index,
                "label": state.label,
                "oscillator_count": len(frequencies),
                "duration_seconds": state_metadata.get("duration_seconds", metadata.get("default_duration_seconds")),
                "attack_ms": state_metadata.get("attack_ms", metadata.get("default_attack_ms")),
                "release_ms": state_metadata.get("release_ms", metadata.get("default_release_ms")),
                "phase_radians": state_metadata.get("phase_radians", metadata.get("default_phase_radians", 0.0)),
                "gain": state_metadata.get("gain", 1.0),
                "source_id": state_metadata.get("source_id"),
                "source_groups": _source_groups_value(state_metadata.get("source_groups")),
                "channel_gains": _channel_gains_mapping(state_metadata.get("channel_gains")),
                "position": _spatial_vector_mapping(state_metadata.get("position")),
                "trajectory": _trajectory_mapping(state_metadata.get("trajectory")),
                "orientation": _spatial_vector_mapping(state_metadata.get("orientation")),
                "spread": _spread_value(state_metadata.get("spread")),
                "distance_model": _distance_model_value(state_metadata.get("distance_model")),
                "min_frequency_hz": min(frequencies) if frequencies else None,
                "max_frequency_hz": max(frequencies) if frequencies else None,
                "max_amplitude": max((abs(amplitude) for amplitude in amplitudes), default=0.0),
                "sample_oscillators": [
                    {"hz": unit.frequency_index, "amplitude": unit.amplitude} for unit in state.units[:5]
                ],
            }
        )

    return {
        "artifact": str(artifact_path),
        "format": metadata.get("format"),
        "arwif_version": metadata.get("arwif_version"),
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "channel_layout": metadata.get("channel_layout"),
        "listener_anchor": _spatial_vector_mapping(metadata.get("listener_anchor")),
        "reference_frame": metadata.get("reference_frame"),
        "playback_model": metadata.get("playback_model"),
        "frequency_unit": metadata.get("frequency_unit"),
        "sample_rate_hz": metadata.get("sample_rate_hz"),
        "default_duration_seconds": metadata.get("default_duration_seconds"),
        "default_attack_ms": metadata.get("default_attack_ms"),
        "default_release_ms": metadata.get("default_release_ms"),
        "default_phase_radians": metadata.get("default_phase_radians"),
        "normalize": metadata.get("normalize"),
        "legacy_mode": validation_report.stats.get("legacy_mode", False),
        "is_valid": validation_report.is_valid,
        "errors": list(validation_report.errors),
        "warnings": list(validation_report.warnings),
        "state_count": len(library.states),
        "oscillator_count": oscillator_count,
        "max_frequency_hz": max_frequency_hz,
        "state_labels": labels,
        "spatial_summary": _spatial_summary(metadata, state_summaries),
        "states": state_summaries,
    }


def _spatial_summary(metadata: dict[str, Any], state_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    channel_layout = metadata.get("channel_layout")
    declared_channels = list(CHANNEL_LAYOUT_CHANNELS.get(channel_layout, ())) if isinstance(channel_layout, str) else []
    listener_anchor = _spatial_vector_mapping(metadata.get("listener_anchor"))
    active_channels = sorted(
        {
            channel_name
            for state in state_summaries
            for channel_name, gain in state.get("channel_gains", {}).items()
            if float(gain) != 0.0
        }
    )
    states_with_channel_gains = sum(1 for state in state_summaries if state.get("channel_gains"))
    positioned_states = sum(1 for state in state_summaries if state.get("position"))
    states_with_trajectory = sum(1 for state in state_summaries if state.get("trajectory"))
    trajectory_point_count = sum(len(state.get("trajectory", [])) for state in state_summaries)
    states_with_orientation = sum(1 for state in state_summaries if state.get("orientation"))
    states_with_spread = sum(1 for state in state_summaries if state.get("spread") is not None)
    states_with_source_id = sum(1 for state in state_summaries if isinstance(state.get("source_id"), str) and state.get("source_id"))
    source_groups = sorted(
        {
            group_name
            for state in state_summaries
            for group_name in state.get("source_groups", [])
            if isinstance(group_name, str) and group_name
        }
    )
    distance_models = sorted(
        {
            str(state.get("distance_model"))
            for state in state_summaries
            if isinstance(state.get("distance_model"), str)
        }
    )
    return {
        "channel_layout": channel_layout,
        "declared_channels": declared_channels,
        "listener_anchor": listener_anchor,
        "reference_frame": metadata.get("reference_frame"),
        "active_channels": active_channels,
        "states_with_channel_gains": states_with_channel_gains,
        "positioned_states": positioned_states,
        "states_with_trajectory": states_with_trajectory,
        "trajectory_point_count": trajectory_point_count,
        "states_with_orientation": states_with_orientation,
        "states_with_spread": states_with_spread,
        "states_with_source_id": states_with_source_id,
        "source_groups": source_groups,
        "distance_models": distance_models,
    }
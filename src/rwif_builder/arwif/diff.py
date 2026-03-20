from __future__ import annotations

from pathlib import Path
from typing import Any

from ..writer.rwif_writer import AtomicWaveUnit
from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import load_wave_library
from .validation import validate_arwif_artifact

_METADATA_KEYS = (
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
    "sample_rate_hz",
    "default_duration_seconds",
    "default_attack_ms",
    "default_release_ms",
    "default_phase_radians",
    "normalize",
    "title",
    "description",
)


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
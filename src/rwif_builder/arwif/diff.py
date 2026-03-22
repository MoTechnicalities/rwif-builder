from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import AtomicWaveUnit
from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import load_wave_library
from .validation import CHANNEL_LAYOUT_CHANNELS
from .validation import ROOM_DIMENSION_KEYS
from .validation import validate_arwif_artifact

_METADATA_KEYS = (
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
    "channel_layout",
    "listener_anchor",
    "reference_frame",
    "room",
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


def _room_dimensions_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key in ROOM_DIMENSION_KEYS:
        component = value.get(key)
        if not isinstance(component, (int, float)) or not math.isfinite(float(component)) or float(component) <= 0.0:
            return {}
        result[key] = float(component)
    return result


def _listening_zones_mapping(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    zones: list[dict[str, Any]] = []
    for zone_document in value:
        if not isinstance(zone_document, dict):
            return []
        zone_id = zone_document.get("zone_id")
        radius_m = zone_document.get("radius_m")
        anchor = _spatial_vector_mapping(zone_document.get("anchor"))
        if not isinstance(zone_id, str) or not zone_id or not anchor:
            return []
        if not isinstance(radius_m, (int, float)) or not math.isfinite(float(radius_m)) or float(radius_m) <= 0.0:
            return []
        zone_entry = {
            "zone_id": zone_id,
            "anchor": anchor,
            "radius_m": float(radius_m),
        }
        intent = zone_document.get("intent")
        if isinstance(intent, str) and intent:
            zone_entry["intent"] = intent
        zones.append(zone_entry)
    return zones


def _speakers_mapping(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    speakers: list[dict[str, Any]] = []
    for speaker_document in value:
        if not isinstance(speaker_document, dict):
            return []
        speaker_id = speaker_document.get("speaker_id")
        anchor = _spatial_vector_mapping(speaker_document.get("anchor"))
        if not isinstance(speaker_id, str) or not speaker_id or not anchor:
            return []
        speaker_entry = {
            "speaker_id": speaker_id,
            "anchor": anchor,
        }
        channel = speaker_document.get("channel")
        if isinstance(channel, str) and channel:
            speaker_entry["channel"] = channel
        role = speaker_document.get("role")
        if isinstance(role, str) and role:
            speaker_entry["role"] = role
        speakers.append(speaker_entry)
    return speakers


def _room_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    room: dict[str, Any] = {}
    dimensions = _room_dimensions_mapping(value.get("dimensions"))
    if dimensions:
        room["dimensions"] = dimensions
    geometry_reference = value.get("geometry_reference")
    if isinstance(geometry_reference, dict):
        geometry_reference_mapping = {
            key: geometry_reference[key]
            for key in ("geometry_id", "geometry_class")
            if isinstance(geometry_reference.get(key), str) and geometry_reference.get(key)
        }
        if geometry_reference_mapping:
            room["geometry_reference"] = geometry_reference_mapping
    surface_profile = value.get("surface_profile")
    if isinstance(surface_profile, str) and surface_profile:
        room["surface_profile"] = surface_profile
    surface_treatment = value.get("surface_treatment")
    if isinstance(surface_treatment, dict):
        surface_treatment_mapping = {
            key: surface_treatment[key]
            for key in ("absorption", "diffusion")
            if isinstance(surface_treatment.get(key), str) and surface_treatment.get(key)
        }
        if surface_treatment_mapping:
            room["surface_treatment"] = surface_treatment_mapping
    reflection_policy = value.get("reflection_policy")
    if isinstance(reflection_policy, dict):
        reflection_policy_mapping = {
            key: reflection_policy[key]
            for key in ("style", "early_reflections", "late_reverb")
            if isinstance(reflection_policy.get(key), str) and reflection_policy.get(key)
        }
        if reflection_policy_mapping:
            room["reflection_policy"] = reflection_policy_mapping
    renderer_adaptation_hints = value.get("renderer_adaptation_hints")
    if isinstance(renderer_adaptation_hints, dict):
        renderer_adaptation_mapping = {
            key: renderer_adaptation_hints[key]
            for key in ("target_playback", "spatial_priority", "downmix_policy")
            if isinstance(renderer_adaptation_hints.get(key), str) and renderer_adaptation_hints.get(key)
        }
        if renderer_adaptation_mapping:
            room["renderer_adaptation_hints"] = renderer_adaptation_mapping
    listening_zones = _listening_zones_mapping(value.get("listening_zones"))
    if listening_zones:
        room["listening_zones"] = listening_zones
    speakers = _speakers_mapping(value.get("speakers"))
    if speakers:
        room["speakers"] = speakers
    return room


def _trajectory_sequences(states: tuple[WaveState, ...]) -> list[list[dict[str, Any]]]:
    return [_trajectory_mapping(dict(state.metadata or {}).get("trajectory")) for state in states]


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
    room = _room_mapping(metadata.get("room"))
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
    states_with_trajectory = sum(1 for state in states if _trajectory_mapping(dict(state.metadata or {}).get("trajectory")))
    trajectory_point_count = sum(
        len(_trajectory_mapping(dict(state.metadata or {}).get("trajectory"))) for state in states
    )
    states_with_orientation = sum(
        1 for state in states if _spatial_vector_mapping(dict(state.metadata or {}).get("orientation"))
    )
    states_with_spread = sum(1 for state in states if _spread_value(dict(state.metadata or {}).get("spread")) is not None)
    states_with_source_id = sum(
        1
        for state in states
        if isinstance(dict(state.metadata or {}).get("source_id"), str) and dict(state.metadata or {}).get("source_id")
    )
    source_groups = sorted(
        {
            group_name
            for state in states
            for group_name in _source_groups_value(dict(state.metadata or {}).get("source_groups"))
        }
    )
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
        "reference_frame": metadata.get("reference_frame"),
        "room_present": bool(room),
        "room_dimensions": dict(room.get("dimensions", {})) if isinstance(room.get("dimensions"), dict) else {},
        "geometry_reference_present": isinstance(room.get("geometry_reference"), dict),
        "room_geometry_id": room.get("geometry_reference", {}).get("geometry_id") if isinstance(room.get("geometry_reference"), dict) else None,
        "room_geometry_class": room.get("geometry_reference", {}).get("geometry_class") if isinstance(room.get("geometry_reference"), dict) else None,
        "room_surface_profile": room.get("surface_profile"),
        "surface_treatment_present": isinstance(room.get("surface_treatment"), dict),
        "room_surface_absorption": room.get("surface_treatment", {}).get("absorption") if isinstance(room.get("surface_treatment"), dict) else None,
        "room_surface_diffusion": room.get("surface_treatment", {}).get("diffusion") if isinstance(room.get("surface_treatment"), dict) else None,
        "reflection_policy_present": isinstance(room.get("reflection_policy"), dict),
        "room_reflection_style": room.get("reflection_policy", {}).get("style") if isinstance(room.get("reflection_policy"), dict) else None,
        "room_early_reflections": room.get("reflection_policy", {}).get("early_reflections") if isinstance(room.get("reflection_policy"), dict) else None,
        "room_late_reverb": room.get("reflection_policy", {}).get("late_reverb") if isinstance(room.get("reflection_policy"), dict) else None,
        "renderer_adaptation_present": isinstance(room.get("renderer_adaptation_hints"), dict),
        "room_target_playback": room.get("renderer_adaptation_hints", {}).get("target_playback") if isinstance(room.get("renderer_adaptation_hints"), dict) else None,
        "room_spatial_priority": room.get("renderer_adaptation_hints", {}).get("spatial_priority") if isinstance(room.get("renderer_adaptation_hints"), dict) else None,
        "room_downmix_policy": room.get("renderer_adaptation_hints", {}).get("downmix_policy") if isinstance(room.get("renderer_adaptation_hints"), dict) else None,
        "listening_zone_count": len(room.get("listening_zones", [])) if isinstance(room.get("listening_zones"), list) else 0,
        "listening_zone_ids": [
            zone.get("zone_id")
            for zone in room.get("listening_zones", [])
            if isinstance(zone, dict) and isinstance(zone.get("zone_id"), str)
        ] if isinstance(room.get("listening_zones"), list) else [],
        "speaker_count": len(room.get("speakers", [])) if isinstance(room.get("speakers"), list) else 0,
        "speaker_ids": [
            speaker.get("speaker_id")
            for speaker in room.get("speakers", [])
            if isinstance(speaker, dict) and isinstance(speaker.get("speaker_id"), str)
        ] if isinstance(room.get("speakers"), list) else [],
        "speaker_channels": sorted(
            speaker.get("channel")
            for speaker in room.get("speakers", [])
            if isinstance(speaker, dict) and isinstance(speaker.get("channel"), str)
        ) if isinstance(room.get("speakers"), list) else [],
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
        "reference_frame_changed": left_summary["reference_frame"] != right_summary["reference_frame"],
        "room_changed": _room_mapping(left_metadata.get("room")) != _room_mapping(right_metadata.get("room")),
        "room_dimensions_changed": left_summary["room_dimensions"] != right_summary["room_dimensions"],
        "geometry_reference_changed": left_summary["geometry_reference_present"] != right_summary["geometry_reference_present"]
        or left_summary["room_geometry_id"] != right_summary["room_geometry_id"]
        or left_summary["room_geometry_class"] != right_summary["room_geometry_class"],
        "room_geometry_id_changed": left_summary["room_geometry_id"] != right_summary["room_geometry_id"],
        "room_geometry_class_changed": left_summary["room_geometry_class"] != right_summary["room_geometry_class"],
        "room_surface_profile_changed": left_summary["room_surface_profile"] != right_summary["room_surface_profile"],
        "surface_treatment_changed": left_summary["surface_treatment_present"] != right_summary["surface_treatment_present"]
        or left_summary["room_surface_absorption"] != right_summary["room_surface_absorption"]
        or left_summary["room_surface_diffusion"] != right_summary["room_surface_diffusion"],
        "room_surface_absorption_changed": left_summary["room_surface_absorption"] != right_summary["room_surface_absorption"],
        "room_surface_diffusion_changed": left_summary["room_surface_diffusion"] != right_summary["room_surface_diffusion"],
        "reflection_policy_changed": left_summary["reflection_policy_present"] != right_summary["reflection_policy_present"]
        or left_summary["room_reflection_style"] != right_summary["room_reflection_style"]
        or left_summary["room_early_reflections"] != right_summary["room_early_reflections"]
        or left_summary["room_late_reverb"] != right_summary["room_late_reverb"],
        "room_reflection_style_changed": left_summary["room_reflection_style"] != right_summary["room_reflection_style"],
        "room_early_reflections_changed": left_summary["room_early_reflections"] != right_summary["room_early_reflections"],
        "room_late_reverb_changed": left_summary["room_late_reverb"] != right_summary["room_late_reverb"],
        "renderer_adaptation_changed": left_summary["renderer_adaptation_present"] != right_summary["renderer_adaptation_present"]
        or left_summary["room_target_playback"] != right_summary["room_target_playback"]
        or left_summary["room_spatial_priority"] != right_summary["room_spatial_priority"]
        or left_summary["room_downmix_policy"] != right_summary["room_downmix_policy"],
        "room_target_playback_changed": left_summary["room_target_playback"] != right_summary["room_target_playback"],
        "room_spatial_priority_changed": left_summary["room_spatial_priority"] != right_summary["room_spatial_priority"],
        "room_downmix_policy_changed": left_summary["room_downmix_policy"] != right_summary["room_downmix_policy"],
        "listening_zones_changed": left_summary["listening_zone_ids"] != right_summary["listening_zone_ids"],
        "listening_zone_count_delta": right_summary["listening_zone_count"] - left_summary["listening_zone_count"],
        "speakers_changed": left_summary["speaker_ids"] != right_summary["speaker_ids"],
        "speaker_count_delta": right_summary["speaker_count"] - left_summary["speaker_count"],
        "speaker_channels_changed": left_summary["speaker_channels"] != right_summary["speaker_channels"],
        "channel_layout_changed": left_summary["channel_layout"] != right_summary["channel_layout"],
        "active_channels_changed": left_summary["active_channels"] != right_summary["active_channels"],
        "states_with_channel_gains_delta": (
            right_summary["states_with_channel_gains"] - left_summary["states_with_channel_gains"]
        ),
        "positioned_states_delta": right_summary["positioned_states"] - left_summary["positioned_states"],
        "trajectories_changed": _trajectory_sequences(left_states) != _trajectory_sequences(right_states),
        "states_with_trajectory_delta": (
            right_summary["states_with_trajectory"] - left_summary["states_with_trajectory"]
        ),
        "trajectory_point_count_delta": (
            right_summary["trajectory_point_count"] - left_summary["trajectory_point_count"]
        ),
        "states_with_orientation_delta": (
            right_summary["states_with_orientation"] - left_summary["states_with_orientation"]
        ),
        "states_with_spread_delta": right_summary["states_with_spread"] - left_summary["states_with_spread"],
        "states_with_source_id_delta": (
            right_summary["states_with_source_id"] - left_summary["states_with_source_id"]
        ),
        "source_groups_changed": left_summary["source_groups"] != right_summary["source_groups"],
        "distance_models_changed": left_summary["distance_models"] != right_summary["distance_models"],
    }
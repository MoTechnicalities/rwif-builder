from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import load_wave_library
from .validation import CHANNEL_LAYOUT_CHANNELS
from .validation import ROOM_DIMENSION_KEYS
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
        coverage_intent = speaker_document.get("coverage_intent")
        if isinstance(coverage_intent, str) and coverage_intent:
            speaker_entry["coverage_intent"] = coverage_intent
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
        "metadata": _library_metadata_extras(metadata),
        "realm_references": _realm_references(metadata),
        "room": _room_mapping(metadata.get("room")),
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


def _library_metadata_extras(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in metadata.items()
        if key not in _LIBRARY_SPEC_KEYS and key not in _LIBRARY_INTERNAL_KEYS
    }


def _realm_references(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw_references = _library_metadata_extras(metadata).get("related_realms")
    if raw_references is None:
        raw_references = _library_metadata_extras(metadata).get("realm_references")
    if not isinstance(raw_references, list):
        return []

    references: list[dict[str, Any]] = []
    for entry in raw_references:
        if not isinstance(entry, dict):
            continue
        realm = entry.get("realm")
        if not isinstance(realm, str) or not realm:
            continue
        references.append(dict(entry))
    return references


def _spatial_summary(metadata: dict[str, Any], state_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    channel_layout = metadata.get("channel_layout")
    declared_channels = list(CHANNEL_LAYOUT_CHANNELS.get(channel_layout, ())) if isinstance(channel_layout, str) else []
    listener_anchor = _spatial_vector_mapping(metadata.get("listener_anchor"))
    room = _room_mapping(metadata.get("room"))
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
        "listening_zone_intents": sorted(
            {
                zone.get("intent")
                for zone in room.get("listening_zones", [])
                if isinstance(zone, dict) and isinstance(zone.get("intent"), str)
            }
        ) if isinstance(room.get("listening_zones"), list) else [],
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
        "speaker_roles": sorted(
            {
                speaker.get("role")
                for speaker in room.get("speakers", [])
                if isinstance(speaker, dict) and isinstance(speaker.get("role"), str)
            }
        ) if isinstance(room.get("speakers"), list) else [],
        "speaker_coverage_intents": sorted(
            {
                speaker.get("coverage_intent")
                for speaker in room.get("speakers", [])
                if isinstance(speaker, dict) and isinstance(speaker.get("coverage_intent"), str)
            }
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
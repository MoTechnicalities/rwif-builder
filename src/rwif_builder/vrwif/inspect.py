from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from .validation import validate_vrwif_spec


def _load_spec_document(spec_path: Path) -> dict[str, Any] | None:
    try:
        with spec_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except Exception:
        return None
    return document if isinstance(document, dict) else None


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


def _vector_magnitude(value: dict[str, float]) -> float | None:
    if not value:
        return None
    return math.sqrt(sum(component * component for component in value.values()))


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


def _object_groups_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [group_name for group_name in value if isinstance(group_name, str) and group_name]


def _object_summary(object_document: Any, index: int) -> dict[str, Any]:
    object_mapping = dict(object_document) if isinstance(object_document, dict) else {}
    object_id = object_mapping.get("object_id") if isinstance(object_mapping.get("object_id"), str) else None
    object_groups = _object_groups_value(object_mapping.get("object_groups"))
    trajectory = _trajectory_mapping(object_mapping.get("trajectory"))
    return {
        "index": index,
        "object_key": object_id or f"object:{index}",
        "object_id": object_id,
        "object_groups": object_groups,
        "appearance_class": object_mapping.get("appearance_class", object_mapping.get("class")),
        "position": _spatial_vector_mapping(object_mapping.get("position")),
        "orientation": _spatial_vector_mapping(object_mapping.get("orientation")),
        "transform": dict(object_mapping.get("transform")) if isinstance(object_mapping.get("transform"), dict) else {},
        "trajectory": trajectory,
        "state": object_mapping.get("state"),
        "visibility": object_mapping.get("visibility"),
    }


def _camera_summary(camera_document: Any) -> dict[str, Any]:
    camera_mapping = dict(camera_document) if isinstance(camera_document, dict) else {}
    trajectory = _trajectory_mapping(camera_mapping.get("trajectory"))
    return {
        "camera_id": camera_mapping.get("camera_id"),
        "position": _spatial_vector_mapping(camera_mapping.get("position")),
        "orientation": _spatial_vector_mapping(camera_mapping.get("orientation")),
        "trajectory": trajectory,
        "framing_intent": camera_mapping.get("framing_intent"),
    }


def _lighting_summaries(lighting_document: Any) -> list[dict[str, Any]]:
    if not isinstance(lighting_document, list):
        return []
    summaries: list[dict[str, Any]] = []
    for index, light_document in enumerate(lighting_document):
        light_mapping = dict(light_document) if isinstance(light_document, dict) else {}
        summaries.append(
            {
                "index": index,
                "light_id": light_mapping.get("light_id"),
                "position": _spatial_vector_mapping(light_mapping.get("position")),
                "direction": _spatial_vector_mapping(light_mapping.get("direction")),
                "intensity": light_mapping.get("intensity"),
                "color": light_mapping.get("color"),
                "temperature_kelvin": light_mapping.get("temperature_kelvin"),
            }
        )
    return summaries


def _light_temperature_range(lighting_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    temperatures = [
        float(summary["temperature_kelvin"])
        for summary in lighting_summaries
        if isinstance(summary.get("temperature_kelvin"), (int, float))
    ]
    if not temperatures:
        return None
    return {
        "min": min(temperatures),
        "max": max(temperatures),
    }


def _light_intensity_range(lighting_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    intensities = [
        float(summary["intensity"])
        for summary in lighting_summaries
        if isinstance(summary.get("intensity"), (int, float))
    ]
    if not intensities:
        return None
    return {
        "min": min(intensities),
        "max": max(intensities),
    }

def _object_distance_from_origin_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    distances = [
        distance
        for summary in object_summaries
        for distance in [_vector_magnitude(summary.get("position") or {})]
        if distance is not None
    ]
    if not distances:
        return None
    return {
        "min": min(distances),
        "max": max(distances),
    }


def _trajectory_duration(trajectory: list[dict[str, Any]]) -> float | None:
    if not trajectory:
        return None
    offsets = [
        float(keyframe["offset_seconds"])
        for keyframe in trajectory
        if isinstance(keyframe, dict) and isinstance(keyframe.get("offset_seconds"), (int, float))
    ]
    if not offsets:
        return None
    return max(offsets) - min(offsets)


def _trajectory_path_length(trajectory: list[dict[str, Any]]) -> float | None:
    if not trajectory:
        return None
    positions = [
        keyframe.get("position")
        for keyframe in trajectory
        if isinstance(keyframe, dict) and isinstance(keyframe.get("position"), dict)
    ]
    if len(positions) < 2:
        return 0.0 if positions else None

    path_length = 0.0
    for left_position, right_position in zip(positions, positions[1:]):
        path_length += math.sqrt(
            sum(
                (float(right_position.get(axis, 0.0)) - float(left_position.get(axis, 0.0))) ** 2
                for axis in ("x", "y", "z")
            )
        )
    return path_length


def _trajectory_displacement(trajectory: list[dict[str, Any]]) -> float | None:
    if not trajectory:
        return None
    positions = [
        keyframe.get("position")
        for keyframe in trajectory
        if isinstance(keyframe, dict) and isinstance(keyframe.get("position"), dict)
    ]
    if len(positions) < 2:
        return 0.0 if positions else None
    left_position = positions[0]
    right_position = positions[-1]
    return math.sqrt(
        sum(
            (float(right_position.get(axis, 0.0)) - float(left_position.get(axis, 0.0))) ** 2
            for axis in ("x", "y", "z")
        )
    )


def _object_trajectory_duration_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    durations = [
        duration
        for summary in object_summaries
        for duration in [_trajectory_duration(summary.get("trajectory") or [])]
        if duration is not None
    ]
    if not durations:
        return None
    return {
        "min": min(durations),
        "max": max(durations),
    }


def _object_trajectory_path_length_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    path_lengths = [
        path_length
        for summary in object_summaries
        for path_length in [_trajectory_path_length(summary.get("trajectory") or [])]
        if path_length is not None
    ]
    if not path_lengths:
        return None
    return {
        "min": min(path_lengths),
        "max": max(path_lengths),
    }


def _object_trajectory_displacement_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    displacements = [
        displacement
        for summary in object_summaries
        for displacement in [_trajectory_displacement(summary.get("trajectory") or [])]
        if displacement is not None
    ]
    if not displacements:
        return None
    return {
        "min": min(displacements),
        "max": max(displacements),
    }


def _trajectory_average_speed(trajectory: list[dict[str, Any]]) -> float | None:
    duration = _trajectory_duration(trajectory)
    if duration is None:
        return None
    if duration == 0.0:
        return 0.0
    path_length = _trajectory_path_length(trajectory)
    if path_length is None:
        return None
    return path_length / duration


def _trajectory_peak_speed(trajectory: list[dict[str, Any]]) -> float | None:
    if not trajectory:
        return None
    keyframes = [
        keyframe
        for keyframe in trajectory
        if isinstance(keyframe, dict)
        and isinstance(keyframe.get("position"), dict)
        and isinstance(keyframe.get("offset_seconds"), (int, float))
    ]
    if len(keyframes) < 2:
        return 0.0 if keyframes else None

    segment_speeds: list[float] = []
    for left_keyframe, right_keyframe in zip(keyframes, keyframes[1:]):
        duration = float(right_keyframe.get("offset_seconds", 0.0)) - float(left_keyframe.get("offset_seconds", 0.0))
        if duration <= 0.0:
            continue
        left_position = left_keyframe.get("position") or {}
        right_position = right_keyframe.get("position") or {}
        distance = math.sqrt(
            sum(
                (float(right_position.get(axis, 0.0)) - float(left_position.get(axis, 0.0))) ** 2
                for axis in ("x", "y", "z")
            )
        )
        segment_speeds.append(distance / duration)
    return max(segment_speeds, default=0.0)


def _trajectory_speed_standard_deviation(trajectory: list[dict[str, Any]]) -> float | None:
    if not trajectory:
        return None
    keyframes = [
        keyframe
        for keyframe in trajectory
        if isinstance(keyframe, dict)
        and isinstance(keyframe.get("position"), dict)
        and isinstance(keyframe.get("offset_seconds"), (int, float))
    ]
    if len(keyframes) < 2:
        return 0.0 if keyframes else None

    segment_speeds: list[float] = []
    for left_keyframe, right_keyframe in zip(keyframes, keyframes[1:]):
        duration = float(right_keyframe.get("offset_seconds", 0.0)) - float(left_keyframe.get("offset_seconds", 0.0))
        if duration <= 0.0:
            continue
        left_position = left_keyframe.get("position") or {}
        right_position = right_keyframe.get("position") or {}
        distance = math.sqrt(
            sum(
                (float(right_position.get(axis, 0.0)) - float(left_position.get(axis, 0.0))) ** 2
                for axis in ("x", "y", "z")
            )
        )
        segment_speeds.append(distance / duration)
    if len(segment_speeds) < 2:
        return 0.0
    mean_speed = sum(segment_speeds) / len(segment_speeds)
    variance = sum((segment_speed - mean_speed) ** 2 for segment_speed in segment_speeds) / len(segment_speeds)
    return math.sqrt(variance)


def _trajectory_straightness(trajectory: list[dict[str, Any]]) -> float | None:
    path_length = _trajectory_path_length(trajectory)
    if path_length is None:
        return None
    if path_length == 0.0:
        return 1.0
    displacement = _trajectory_displacement(trajectory)
    if displacement is None:
        return None
    return displacement / path_length


def _trajectory_turn_angles_degrees(trajectory: list[dict[str, Any]]) -> list[float] | None:
    if not trajectory:
        return None
    positions = [
        keyframe.get("position")
        for keyframe in trajectory
        if isinstance(keyframe, dict) and isinstance(keyframe.get("position"), dict)
    ]
    if len(positions) < 3:
        return [] if positions else None

    turn_angles: list[float] = []
    for left_position, center_position, right_position in zip(positions, positions[1:], positions[2:]):
        left_vector = [
            float(center_position.get(axis, 0.0)) - float(left_position.get(axis, 0.0))
            for axis in ("x", "y", "z")
        ]
        right_vector = [
            float(right_position.get(axis, 0.0)) - float(center_position.get(axis, 0.0))
            for axis in ("x", "y", "z")
        ]
        left_magnitude = math.sqrt(sum(component * component for component in left_vector))
        right_magnitude = math.sqrt(sum(component * component for component in right_vector))
        if left_magnitude == 0.0 or right_magnitude == 0.0:
            continue
        cosine = sum(left * right for left, right in zip(left_vector, right_vector, strict=True)) / (
            left_magnitude * right_magnitude
        )
        turn_angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
    return turn_angles


def _trajectory_turn_angle_degrees(trajectory: list[dict[str, Any]]) -> float | None:
    turn_angles = _trajectory_turn_angles_degrees(trajectory)
    if turn_angles is None:
        return None
    return sum(turn_angles)


def _trajectory_peak_turn_angle_degrees(trajectory: list[dict[str, Any]]) -> float | None:
    turn_angles = _trajectory_turn_angles_degrees(trajectory)
    if turn_angles is None:
        return None
    return max(turn_angles, default=0.0)


def _trajectory_turn_count(trajectory: list[dict[str, Any]]) -> int | None:
    turn_angles = _trajectory_turn_angles_degrees(trajectory)
    if turn_angles is None:
        return None
    return sum(1 for turn_angle in turn_angles if turn_angle > 0.0)


def _trajectory_average_turn_angle_degrees(trajectory: list[dict[str, Any]]) -> float | None:
    turn_angles = _trajectory_turn_angles_degrees(trajectory)
    if turn_angles is None:
        return None
    if not turn_angles:
        return 0.0
    return sum(turn_angles) / len(turn_angles)


def _trajectory_turn_angle_standard_deviation_degrees(trajectory: list[dict[str, Any]]) -> float | None:
    turn_angles = _trajectory_turn_angles_degrees(trajectory)
    if turn_angles is None:
        return None
    if len(turn_angles) <= 1:
        return 0.0
    average_turn_angle = sum(turn_angles) / len(turn_angles)
    variance = sum((turn_angle - average_turn_angle) ** 2 for turn_angle in turn_angles) / len(turn_angles)
    return math.sqrt(variance)


def _object_trajectory_average_speed_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    average_speeds = [
        average_speed
        for summary in object_summaries
        for average_speed in [_trajectory_average_speed(summary.get("trajectory") or [])]
        if average_speed is not None
    ]
    if not average_speeds:
        return None
    return {
        "min": min(average_speeds),
        "max": max(average_speeds),
    }


def _object_trajectory_peak_speed_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    peak_speeds = [
        peak_speed
        for summary in object_summaries
        for peak_speed in [_trajectory_peak_speed(summary.get("trajectory") or [])]
        if peak_speed is not None
    ]
    if not peak_speeds:
        return None
    return {
        "min": min(peak_speeds),
        "max": max(peak_speeds),
    }


def _object_trajectory_speed_standard_deviation_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    speed_standard_deviations = [
        speed_standard_deviation
        for summary in object_summaries
        for speed_standard_deviation in [_trajectory_speed_standard_deviation(summary.get("trajectory") or [])]
        if speed_standard_deviation is not None
    ]
    if not speed_standard_deviations:
        return None
    return {
        "min": min(speed_standard_deviations),
        "max": max(speed_standard_deviations),
    }


def _object_trajectory_straightness_range(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    straightness_values = [
        straightness
        for summary in object_summaries
        for straightness in [_trajectory_straightness(summary.get("trajectory") or [])]
        if straightness is not None
    ]
    if not straightness_values:
        return None
    return {
        "min": min(straightness_values),
        "max": max(straightness_values),
    }


def _object_trajectory_turn_angle_range_degrees(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    turn_angles = [
        turn_angle
        for summary in object_summaries
        for turn_angle in [_trajectory_turn_angle_degrees(summary.get("trajectory") or [])]
        if turn_angle is not None
    ]
    if not turn_angles:
        return None
    return {
        "min": min(turn_angles),
        "max": max(turn_angles),
    }


def _object_trajectory_peak_turn_angle_range_degrees(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    peak_turn_angles = [
        peak_turn_angle
        for summary in object_summaries
        for peak_turn_angle in [_trajectory_peak_turn_angle_degrees(summary.get("trajectory") or [])]
        if peak_turn_angle is not None
    ]
    if not peak_turn_angles:
        return None
    return {
        "min": min(peak_turn_angles),
        "max": max(peak_turn_angles),
    }


def _object_trajectory_turn_count_range(object_summaries: list[dict[str, Any]]) -> dict[str, int] | None:
    turn_counts = [
        turn_count
        for summary in object_summaries
        for turn_count in [_trajectory_turn_count(summary.get("trajectory") or [])]
        if turn_count is not None
    ]
    if not turn_counts:
        return None
    return {
        "min": min(turn_counts),
        "max": max(turn_counts),
    }


def _object_trajectory_average_turn_angle_range_degrees(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    average_turn_angles = [
        average_turn_angle
        for summary in object_summaries
        for average_turn_angle in [_trajectory_average_turn_angle_degrees(summary.get("trajectory") or [])]
        if average_turn_angle is not None
    ]
    if not average_turn_angles:
        return None
    return {
        "min": min(average_turn_angles),
        "max": max(average_turn_angles),
    }


def _object_trajectory_turn_angle_standard_deviation_range_degrees(object_summaries: list[dict[str, Any]]) -> dict[str, float] | None:
    turn_angle_standard_deviations = [
        turn_angle_standard_deviation
        for summary in object_summaries
        for turn_angle_standard_deviation in [_trajectory_turn_angle_standard_deviation_degrees(summary.get("trajectory") or [])]
        if turn_angle_standard_deviation is not None
    ]
    if not turn_angle_standard_deviations:
        return None
    return {
        "min": min(turn_angle_standard_deviations),
        "max": max(turn_angle_standard_deviations),
    }


def _document_metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _realm_references(document: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = _document_metadata(document)
    raw_references = metadata.get("related_realms")
    if raw_references is None:
        raw_references = metadata.get("realm_references")
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


def _scene_summary(
    document: dict[str, Any],
    object_summaries: list[dict[str, Any]],
    camera_summary: dict[str, Any],
    lighting_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    object_distance_range = _object_distance_from_origin_range(object_summaries)
    object_trajectory_duration_range = _object_trajectory_duration_range(object_summaries)
    object_trajectory_path_length_range = _object_trajectory_path_length_range(object_summaries)
    object_trajectory_displacement_range = _object_trajectory_displacement_range(object_summaries)
    object_trajectory_average_speed_range = _object_trajectory_average_speed_range(object_summaries)
    object_trajectory_peak_speed_range = _object_trajectory_peak_speed_range(object_summaries)
    object_trajectory_speed_standard_deviation_range = _object_trajectory_speed_standard_deviation_range(object_summaries)
    object_trajectory_straightness_range = _object_trajectory_straightness_range(object_summaries)
    object_trajectory_turn_angle_range_degrees = _object_trajectory_turn_angle_range_degrees(object_summaries)
    object_trajectory_peak_turn_angle_range_degrees = _object_trajectory_peak_turn_angle_range_degrees(object_summaries)
    object_trajectory_turn_count_range = _object_trajectory_turn_count_range(object_summaries)
    object_trajectory_average_turn_angle_range_degrees = _object_trajectory_average_turn_angle_range_degrees(object_summaries)
    object_trajectory_turn_angle_standard_deviation_range_degrees = _object_trajectory_turn_angle_standard_deviation_range_degrees(object_summaries)
    light_temperature_range = _light_temperature_range(lighting_summaries)
    light_intensity_range = _light_intensity_range(lighting_summaries)
    camera_distance_from_origin = _vector_magnitude(camera_summary.get("position") or {})
    camera_trajectory_duration = _trajectory_duration(camera_summary.get("trajectory") or [])
    camera_trajectory_path_length = _trajectory_path_length(camera_summary.get("trajectory") or [])
    camera_trajectory_displacement = _trajectory_displacement(camera_summary.get("trajectory") or [])
    camera_trajectory_average_speed = _trajectory_average_speed(camera_summary.get("trajectory") or [])
    camera_trajectory_peak_speed = _trajectory_peak_speed(camera_summary.get("trajectory") or [])
    camera_trajectory_speed_standard_deviation = _trajectory_speed_standard_deviation(camera_summary.get("trajectory") or [])
    camera_trajectory_straightness = _trajectory_straightness(camera_summary.get("trajectory") or [])
    camera_trajectory_turn_angle_degrees = _trajectory_turn_angle_degrees(camera_summary.get("trajectory") or [])
    camera_trajectory_peak_turn_angle_degrees = _trajectory_peak_turn_angle_degrees(camera_summary.get("trajectory") or [])
    camera_trajectory_turn_count = _trajectory_turn_count(camera_summary.get("trajectory") or [])
    camera_trajectory_average_turn_angle_degrees = _trajectory_average_turn_angle_degrees(camera_summary.get("trajectory") or [])
    camera_trajectory_turn_angle_standard_deviation_degrees = _trajectory_turn_angle_standard_deviation_degrees(
        camera_summary.get("trajectory") or []
    )
    return {
        "scene_id": document.get("scene_id"),
        "reference_frame": document.get("reference_frame"),
        "object_count": len(object_summaries),
        "object_ids": [summary["object_id"] for summary in object_summaries if isinstance(summary.get("object_id"), str)],
        "object_groups": sorted(
            {
                group_name
                for summary in object_summaries
                for group_name in summary.get("object_groups", [])
                if isinstance(group_name, str) and group_name
            }
        ),
        "appearance_classes": sorted(
            {
                str(summary.get("appearance_class"))
                for summary in object_summaries
                if isinstance(summary.get("appearance_class"), str) and summary.get("appearance_class")
            }
        ),
        "object_states": sorted(
            {
                str(summary.get("state"))
                for summary in object_summaries
                if isinstance(summary.get("state"), str) and summary.get("state")
            }
        ),
        "object_visibilities": sorted(
            {
                str(summary.get("visibility"))
                for summary in object_summaries
                if isinstance(summary.get("visibility"), str) and summary.get("visibility")
            }
        ),
        "object_distance_from_origin_total": sum(
            distance
            for summary in object_summaries
            for distance in [_vector_magnitude(summary.get("position") or {})]
            if distance is not None
        ),
        "object_distance_from_origin_range": object_distance_range,
        "positioned_objects": sum(1 for summary in object_summaries if summary.get("position")),
        "objects_with_orientation": sum(1 for summary in object_summaries if summary.get("orientation")),
        "objects_with_trajectory": sum(1 for summary in object_summaries if summary.get("trajectory")),
        "object_trajectory_duration_total": sum(
            duration
            for summary in object_summaries
            for duration in [_trajectory_duration(summary.get("trajectory") or [])]
            if duration is not None
        ),
        "object_trajectory_duration_range": object_trajectory_duration_range,
        "object_trajectory_path_length_total": sum(
            path_length
            for summary in object_summaries
            for path_length in [_trajectory_path_length(summary.get("trajectory") or [])]
            if path_length is not None
        ),
        "object_trajectory_path_length_range": object_trajectory_path_length_range,
        "object_trajectory_displacement_total": sum(
            displacement
            for summary in object_summaries
            for displacement in [_trajectory_displacement(summary.get("trajectory") or [])]
            if displacement is not None
        ),
        "object_trajectory_displacement_range": object_trajectory_displacement_range,
        "object_trajectory_average_speed_total": sum(
            average_speed
            for summary in object_summaries
            for average_speed in [_trajectory_average_speed(summary.get("trajectory") or [])]
            if average_speed is not None
        ),
        "object_trajectory_average_speed_range": object_trajectory_average_speed_range,
        "object_trajectory_peak_speed_total": sum(
            peak_speed
            for summary in object_summaries
            for peak_speed in [_trajectory_peak_speed(summary.get("trajectory") or [])]
            if peak_speed is not None
        ),
        "object_trajectory_peak_speed_range": object_trajectory_peak_speed_range,
        "object_trajectory_speed_standard_deviation_total": sum(
            speed_standard_deviation
            for summary in object_summaries
            for speed_standard_deviation in [_trajectory_speed_standard_deviation(summary.get("trajectory") or [])]
            if speed_standard_deviation is not None
        ),
        "object_trajectory_speed_standard_deviation_range": object_trajectory_speed_standard_deviation_range,
        "object_trajectory_straightness_total": sum(
            straightness
            for summary in object_summaries
            for straightness in [_trajectory_straightness(summary.get("trajectory") or [])]
            if straightness is not None
        ),
        "object_trajectory_straightness_range": object_trajectory_straightness_range,
        "object_trajectory_turn_angle_total_degrees": sum(
            turn_angle
            for summary in object_summaries
            for turn_angle in [_trajectory_turn_angle_degrees(summary.get("trajectory") or [])]
            if turn_angle is not None
        ),
        "object_trajectory_turn_angle_range_degrees": object_trajectory_turn_angle_range_degrees,
        "object_trajectory_peak_turn_angle_total_degrees": sum(
            peak_turn_angle
            for summary in object_summaries
            for peak_turn_angle in [_trajectory_peak_turn_angle_degrees(summary.get("trajectory") or [])]
            if peak_turn_angle is not None
        ),
        "object_trajectory_peak_turn_angle_range_degrees": object_trajectory_peak_turn_angle_range_degrees,
        "object_trajectory_turn_count_total": sum(
            turn_count
            for summary in object_summaries
            for turn_count in [_trajectory_turn_count(summary.get("trajectory") or [])]
            if turn_count is not None
        ),
        "object_trajectory_turn_count_range": object_trajectory_turn_count_range,
        "object_trajectory_average_turn_angle_total_degrees": sum(
            average_turn_angle
            for summary in object_summaries
            for average_turn_angle in [_trajectory_average_turn_angle_degrees(summary.get("trajectory") or [])]
            if average_turn_angle is not None
        ),
        "object_trajectory_average_turn_angle_range_degrees": object_trajectory_average_turn_angle_range_degrees,
        "object_trajectory_turn_angle_standard_deviation_total_degrees": sum(
            turn_angle_standard_deviation
            for summary in object_summaries
            for turn_angle_standard_deviation in [_trajectory_turn_angle_standard_deviation_degrees(summary.get("trajectory") or [])]
            if turn_angle_standard_deviation is not None
        ),
        "object_trajectory_turn_angle_standard_deviation_range_degrees": object_trajectory_turn_angle_standard_deviation_range_degrees,
        "object_trajectory_point_count": sum(len(summary.get("trajectory", [])) for summary in object_summaries),
        "camera_present": bool(camera_summary),
        "camera_distance_from_origin": camera_distance_from_origin,
        "camera_has_trajectory": bool(camera_summary.get("trajectory")),
        "camera_trajectory_duration": camera_trajectory_duration,
        "camera_trajectory_path_length": camera_trajectory_path_length,
        "camera_trajectory_displacement": camera_trajectory_displacement,
        "camera_trajectory_average_speed": camera_trajectory_average_speed,
        "camera_trajectory_peak_speed": camera_trajectory_peak_speed,
        "camera_trajectory_speed_standard_deviation": camera_trajectory_speed_standard_deviation,
        "camera_trajectory_straightness": camera_trajectory_straightness,
        "camera_trajectory_turn_angle_degrees": camera_trajectory_turn_angle_degrees,
        "camera_trajectory_peak_turn_angle_degrees": camera_trajectory_peak_turn_angle_degrees,
        "camera_trajectory_turn_count": camera_trajectory_turn_count,
        "camera_trajectory_average_turn_angle_degrees": camera_trajectory_average_turn_angle_degrees,
        "camera_trajectory_turn_angle_standard_deviation_degrees": camera_trajectory_turn_angle_standard_deviation_degrees,
        "camera_trajectory_point_count": len(camera_summary.get("trajectory", [])),
        "camera_framing_intent": camera_summary.get("framing_intent"),
        "light_count": len(lighting_summaries),
        "light_intensity_total": sum(
            float(summary["intensity"])
            for summary in lighting_summaries
            if isinstance(summary.get("intensity"), (int, float))
        ),
        "light_intensity_range": light_intensity_range,
        "positioned_lights": sum(1 for summary in lighting_summaries if summary.get("position")),
        "directional_lights": sum(1 for summary in lighting_summaries if summary.get("direction")),
        "lights_with_temperature": sum(
            1 for summary in lighting_summaries if isinstance(summary.get("temperature_kelvin"), (int, float))
        ),
        "light_temperature_range_kelvin": light_temperature_range,
        "light_colors": sorted(
            {
                str(summary.get("color"))
                for summary in lighting_summaries
                if isinstance(summary.get("color"), str) and summary.get("color")
            }
        ),
        "light_ids": [summary.get("light_id") for summary in lighting_summaries if isinstance(summary.get("light_id"), str)],
    }


def inspect_vrwif_spec(path: str | Path) -> dict[str, Any]:
    spec_path = Path(path)
    validation_report = validate_vrwif_spec(spec_path)
    document = _load_spec_document(spec_path) or {}

    object_summaries = [
        _object_summary(object_document, index)
        for index, object_document in enumerate(document.get("objects", []) if isinstance(document.get("objects"), list) else [])
    ]
    camera_summary = _camera_summary(document.get("camera")) if isinstance(document.get("camera"), dict) else {}
    lighting_summaries = _lighting_summaries(document.get("lighting"))

    return {
        "spec": str(spec_path),
        "is_valid": validation_report.is_valid,
        "errors": list(validation_report.errors),
        "warnings": list(validation_report.warnings),
        "vrwif_version": document.get("vrwif_version", 1),
        "scene_id": document.get("scene_id"),
        "reference_frame": document.get("reference_frame"),
        "title": document.get("title"),
        "description": document.get("description"),
        "metadata": _document_metadata(document),
        "realm_references": _realm_references(document),
        "object_count": len(object_summaries),
        "scene_summary": _scene_summary(document, object_summaries, camera_summary, lighting_summaries),
        "objects": object_summaries,
        "camera": camera_summary,
        "lighting": lighting_summaries,
    }
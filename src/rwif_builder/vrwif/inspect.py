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


def _scene_summary(
    document: dict[str, Any],
    object_summaries: list[dict[str, Any]],
    camera_summary: dict[str, Any],
    lighting_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
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
        "positioned_objects": sum(1 for summary in object_summaries if summary.get("position")),
        "objects_with_orientation": sum(1 for summary in object_summaries if summary.get("orientation")),
        "objects_with_trajectory": sum(1 for summary in object_summaries if summary.get("trajectory")),
        "object_trajectory_point_count": sum(len(summary.get("trajectory", [])) for summary in object_summaries),
        "camera_present": bool(camera_summary),
        "camera_has_trajectory": bool(camera_summary.get("trajectory")),
        "camera_trajectory_point_count": len(camera_summary.get("trajectory", [])),
        "light_count": len(lighting_summaries),
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
        "object_count": len(object_summaries),
        "scene_summary": _scene_summary(document, object_summaries, camera_summary, lighting_summaries),
        "objects": object_summaries,
        "camera": camera_summary,
        "lighting": lighting_summaries,
    }
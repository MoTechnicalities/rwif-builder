from __future__ import annotations

from pathlib import Path
from typing import Any

from .inspect import inspect_vrwif_spec

_METADATA_KEYS = (
    "vrwif_version",
    "scene_id",
    "reference_frame",
    "title",
    "description",
)


def diff_vrwif_specs(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_path = Path(left)
    right_path = Path(right)

    left_payload = inspect_vrwif_spec(left_path)
    right_payload = inspect_vrwif_spec(right_path)

    metadata_changes = {
        key: {"left": left_payload.get(key), "right": right_payload.get(key)}
        for key in _METADATA_KEYS
        if left_payload.get(key) != right_payload.get(key)
    }

    left_objects = _object_map(left_payload.get("objects"))
    right_objects = _object_map(right_payload.get("objects"))
    left_keys = set(left_objects)
    right_keys = set(right_objects)

    added_objects = sorted(right_keys - left_keys)
    removed_objects = sorted(left_keys - right_keys)
    changed_objects = sorted(
        key for key in left_keys & right_keys if _object_signature(left_objects[key]) != _object_signature(right_objects[key])
    )
    unchanged_objects = sorted(
        key for key in left_keys & right_keys if _object_signature(left_objects[key]) == _object_signature(right_objects[key])
    )

    object_changes = {
        key: _describe_object_change(left_objects[key], right_objects[key])
        for key in changed_objects
    }

    left_scene_summary = dict(left_payload.get("scene_summary") or {})
    right_scene_summary = dict(right_payload.get("scene_summary") or {})

    return {
        "left": str(left_path),
        "right": str(right_path),
        "left_valid": bool(left_payload.get("is_valid", False)),
        "right_valid": bool(right_payload.get("is_valid", False)),
        "metadata_changes": metadata_changes,
        "left_scene_summary": left_scene_summary,
        "right_scene_summary": right_scene_summary,
        "scene_changes": _scene_changes(left_payload, right_payload),
        "added_objects": added_objects,
        "removed_objects": removed_objects,
        "changed_objects": changed_objects,
        "unchanged_objects": unchanged_objects,
        "object_changes": object_changes,
        "change_summary": {
            "metadata_fields_changed": len(metadata_changes),
            "added_objects": len(added_objects),
            "removed_objects": len(removed_objects),
            "changed_objects": len(changed_objects),
            "unchanged_objects": len(unchanged_objects),
        },
    }


def _object_map(objects: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(objects, list):
        return result
    for index, object_summary in enumerate(objects):
        if not isinstance(object_summary, dict):
            continue
        key = str(object_summary.get("object_key") or object_summary.get("object_id") or f"object:{index}")
        if key in result:
            key = f"{key}#{index}"
        result[key] = object_summary
    return result


def _object_signature(object_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        key: object_summary.get(key)
        for key in (
            "object_id",
            "object_groups",
            "appearance_class",
            "position",
            "orientation",
            "transform",
            "trajectory",
            "state",
            "visibility",
        )
    }


def _describe_object_change(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    field_changes = {
        key: {"left": left.get(key), "right": right.get(key)}
        for key in (
            "object_id",
            "object_groups",
            "appearance_class",
            "position",
            "orientation",
            "transform",
            "trajectory",
            "state",
            "visibility",
        )
        if left.get(key) != right.get(key)
    }
    return {"field_changes": field_changes}


def _scene_changes(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> dict[str, Any]:
    left_summary = dict(left_payload.get("scene_summary") or {})
    right_summary = dict(right_payload.get("scene_summary") or {})
    return {
        "reference_frame_changed": left_summary.get("reference_frame") != right_summary.get("reference_frame"),
        "object_groups_changed": left_summary.get("object_groups") != right_summary.get("object_groups"),
        "appearance_classes_changed": left_summary.get("appearance_classes") != right_summary.get("appearance_classes"),
        "positioned_objects_delta": int(right_summary.get("positioned_objects", 0)) - int(left_summary.get("positioned_objects", 0)),
        "objects_with_orientation_delta": int(right_summary.get("objects_with_orientation", 0)) - int(left_summary.get("objects_with_orientation", 0)),
        "objects_with_trajectory_delta": int(right_summary.get("objects_with_trajectory", 0)) - int(left_summary.get("objects_with_trajectory", 0)),
        "object_trajectory_point_count_delta": int(right_summary.get("object_trajectory_point_count", 0)) - int(left_summary.get("object_trajectory_point_count", 0)),
        "camera_changed": left_payload.get("camera") != right_payload.get("camera"),
        "camera_trajectory_changed": (left_payload.get("camera") or {}).get("trajectory") != (right_payload.get("camera") or {}).get("trajectory"),
        "light_count_delta": int(right_summary.get("light_count", 0)) - int(left_summary.get("light_count", 0)),
        "light_ids_changed": left_summary.get("light_ids") != right_summary.get("light_ids"),
    }
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import yaml

from .validation import VRWIF_VERSION
from .validation import validate_vrwif_spec
from .validation import validate_vrwif_spec_document

_VECTOR_AXES = ("x", "y", "z")
_TOP_LEVEL_KEYS = {
    "vrwif_version",
    "scene_id",
    "reference_frame",
    "title",
    "description",
    "objects",
    "camera",
    "lighting",
    "metadata",
}
_OBJECT_KEYS = {
    "object_id",
    "object_groups",
    "class",
    "appearance_class",
    "position",
    "orientation",
    "transform",
    "trajectory",
    "state",
    "visibility",
    "metadata",
}
_CAMERA_KEYS = {
    "camera_id",
    "position",
    "orientation",
    "trajectory",
    "framing_intent",
    "metadata",
}
_LIGHT_KEYS = {
    "light_id",
    "position",
    "direction",
    "intensity",
    "color",
    "temperature_kelvin",
    "metadata",
}


def normalize_vrwif_spec(
    spec: str | Path,
    output: str | Path,
    *,
    format: str | None = None,
) -> dict[str, Any]:
    spec_path = Path(spec)
    output_path = Path(output)

    source_document, load_errors = _load_spec_document(spec_path)
    if source_document is None:
        raise ValueError("; ".join(load_errors))

    source_report = validate_vrwif_spec(spec_path)
    normalized_document, normalization_summary = _normalize_vrwif_document(source_document)
    normalized_report = validate_vrwif_spec_document(normalized_document, source=str(spec_path))
    if not normalized_report.is_valid:
        raise ValueError("generated normalized spec failed validation")

    export_format = _resolve_export_format(output_path, format)
    _write_spec_document(output_path, normalized_document, export_format)

    return {
        "spec": str(spec_path),
        "output": str(output_path),
        "format": export_format,
        "scene_id": normalized_report.stats.get("scene_id"),
        "reference_frame": normalized_report.stats.get("reference_frame"),
        "source_is_valid": source_report.is_valid,
        "source_errors": list(source_report.errors),
        "source_warnings": list(source_report.warnings),
        "normalized_spec_is_valid": normalized_report.is_valid,
        "normalized_spec_errors": list(normalized_report.errors),
        "normalized_spec_warnings": list(normalized_report.warnings),
        "normalized_object_count": int(normalized_report.stats.get("object_count", 0)),
        "normalized_light_count": int(normalized_report.stats.get("light_count", 0)),
        "normalization_summary": normalization_summary,
        "normalized": True,
    }


def _load_spec_document(spec_path: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    try:
        with spec_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except Exception as exc:
        return None, (str(exc),)

    if document is None:
        return None, ("VRWIF spec file is empty",)
    if not isinstance(document, dict):
        return None, ("VRWIF spec must be a mapping",)
    return document, ()


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


def _write_spec_document(output_path: Path, document: dict[str, Any], export_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _deep_copy_document(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy_document(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy_document(item) for item in value]
    return value


def _normalize_string(value: Any, *, lower: bool = False) -> Any:
    if not isinstance(value, str):
        return _deep_copy_document(value)
    normalized = value.strip()
    if lower:
        normalized = normalized.lower()
    return normalized


def _normalize_vector(value: Any) -> Any:
    if not isinstance(value, dict):
        return _deep_copy_document(value)
    return {
        axis: float(value[axis]) if _is_finite_number(value.get(axis)) else _deep_copy_document(value.get(axis))
        for axis in _VECTOR_AXES
    }


def _normalize_trajectory(value: Any, summary: dict[str, int], summary_key: str) -> Any:
    if not isinstance(value, list):
        return _deep_copy_document(value)

    normalized: list[Any] = []
    sortable = True
    for keyframe in value:
        if not isinstance(keyframe, dict):
            sortable = False
            normalized.append(_deep_copy_document(keyframe))
            continue

        entry: dict[str, Any] = {}
        offset_seconds = keyframe.get("offset_seconds")
        if _is_finite_number(offset_seconds) and float(offset_seconds) >= 0.0:
            entry["offset_seconds"] = float(offset_seconds)
        else:
            sortable = False
            entry["offset_seconds"] = _deep_copy_document(offset_seconds)

        entry["position"] = _normalize_vector(keyframe.get("position"))
        normalized.append(entry)

    if sortable:
        sorted_trajectory = sorted(normalized, key=lambda keyframe: keyframe["offset_seconds"])
        if sorted_trajectory != normalized:
            summary[summary_key] += 1
        return sorted_trajectory
    return normalized


def _normalize_object_groups(value: Any, summary: dict[str, int]) -> Any:
    if not isinstance(value, list):
        return _deep_copy_document(value)

    normalized_groups = [_normalize_string(group_name) for group_name in value]
    if not all(isinstance(group_name, str) and group_name for group_name in normalized_groups):
        return normalized_groups

    deduplicated_groups = sorted(set(normalized_groups))
    if deduplicated_groups != normalized_groups:
        summary["deduplicated_object_groups"] += 1
    return deduplicated_groups


def _normalize_object_document(value: Any, summary: dict[str, int]) -> Any:
    if not isinstance(value, dict):
        return _deep_copy_document(value)

    summary["dropped_unknown_object_fields"] += len([key for key in value if key not in _OBJECT_KEYS])
    normalized: dict[str, Any] = {}

    if "object_id" in value:
        normalized["object_id"] = _normalize_string(value.get("object_id"))

    if "object_groups" in value:
        normalized["object_groups"] = _normalize_object_groups(value.get("object_groups"), summary)

    if "appearance_class" in value or "class" in value:
        if "appearance_class" not in value and "class" in value:
            summary["resolved_class_aliases"] += 1
        normalized["appearance_class"] = _normalize_string(value.get("appearance_class", value.get("class")))

    if "position" in value:
        normalized["position"] = _normalize_vector(value.get("position"))

    if "orientation" in value:
        normalized["orientation"] = _normalize_vector(value.get("orientation"))

    if isinstance(value.get("transform"), dict):
        normalized["transform"] = _deep_copy_document(value.get("transform"))
    elif "transform" in value and value.get("transform") is not None:
        normalized["transform"] = _deep_copy_document(value.get("transform"))

    if "trajectory" in value:
        normalized["trajectory"] = _normalize_trajectory(value.get("trajectory"), summary, "sorted_object_trajectories")

    for key in ("state", "visibility"):
        if key in value and value.get(key) is not None:
            normalized[key] = _deep_copy_document(value.get(key))

    if isinstance(value.get("metadata"), dict):
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))
    elif "metadata" in value and value.get("metadata") is not None:
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))

    return normalized


def _normalize_camera_document(value: Any, summary: dict[str, int]) -> Any:
    if not isinstance(value, dict):
        return _deep_copy_document(value)

    summary["dropped_unknown_camera_fields"] += len([key for key in value if key not in _CAMERA_KEYS])
    normalized: dict[str, Any] = {}

    if "camera_id" in value:
        normalized["camera_id"] = _normalize_string(value.get("camera_id"))
    if "position" in value:
        normalized["position"] = _normalize_vector(value.get("position"))
    if "orientation" in value:
        normalized["orientation"] = _normalize_vector(value.get("orientation"))
    if "trajectory" in value:
        normalized["trajectory"] = _normalize_trajectory(value.get("trajectory"), summary, "sorted_camera_trajectory")
    if "framing_intent" in value and value.get("framing_intent") is not None:
        normalized["framing_intent"] = _normalize_string(value.get("framing_intent"))
    if isinstance(value.get("metadata"), dict):
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))
    elif "metadata" in value and value.get("metadata") is not None:
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))

    return normalized


def _normalize_light_document(value: Any, summary: dict[str, int]) -> Any:
    if not isinstance(value, dict):
        return _deep_copy_document(value)

    summary["dropped_unknown_light_fields"] += len([key for key in value if key not in _LIGHT_KEYS])
    normalized: dict[str, Any] = {}

    if "light_id" in value:
        normalized["light_id"] = _normalize_string(value.get("light_id"))
    if "position" in value:
        normalized["position"] = _normalize_vector(value.get("position"))
    if "direction" in value:
        normalized["direction"] = _normalize_vector(value.get("direction"))
    if "intensity" in value:
        intensity = value.get("intensity")
        normalized["intensity"] = float(intensity) if _is_finite_number(intensity) else _deep_copy_document(intensity)
    if "color" in value and value.get("color") is not None:
        normalized["color"] = _normalize_string(value.get("color"))
    if "temperature_kelvin" in value and value.get("temperature_kelvin") is not None:
        temperature = value.get("temperature_kelvin")
        normalized["temperature_kelvin"] = float(temperature) if _is_finite_number(temperature) else _deep_copy_document(temperature)
    if isinstance(value.get("metadata"), dict):
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))
    elif "metadata" in value and value.get("metadata") is not None:
        normalized["metadata"] = _deep_copy_document(value.get("metadata"))

    return normalized


def _normalize_vrwif_document(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    summary = {
        "inserted_vrwif_version": 0,
        "resolved_class_aliases": 0,
        "deduplicated_object_groups": 0,
        "sorted_object_trajectories": 0,
        "sorted_camera_trajectory": 0,
        "reordered_objects": 0,
        "reordered_lights": 0,
        "dropped_unknown_top_level_fields": len([key for key in document if key not in _TOP_LEVEL_KEYS]),
        "dropped_unknown_object_fields": 0,
        "dropped_unknown_camera_fields": 0,
        "dropped_unknown_light_fields": 0,
    }

    normalized: dict[str, Any] = {"vrwif_version": VRWIF_VERSION}
    if document.get("vrwif_version") != VRWIF_VERSION:
        summary["inserted_vrwif_version"] = 1

    if "scene_id" in document:
        normalized["scene_id"] = _normalize_string(document.get("scene_id"))
    if "reference_frame" in document:
        normalized["reference_frame"] = _normalize_string(document.get("reference_frame"), lower=True)
    if "title" in document and document.get("title") is not None:
        normalized["title"] = _normalize_string(document.get("title"))
    if "description" in document and document.get("description") is not None:
        normalized["description"] = _normalize_string(document.get("description"))

    objects = document.get("objects")
    if isinstance(objects, list):
        normalized_objects = [_normalize_object_document(object_document, summary) for object_document in objects]
        sorted_objects = sorted(
            enumerate(normalized_objects),
            key=lambda item: (
                0,
                item[1].get("object_id"),
            )
            if isinstance(item[1], dict) and isinstance(item[1].get("object_id"), str) and item[1].get("object_id")
            else (1, item[0]),
        )
        if [index for index, _ in sorted_objects] != list(range(len(normalized_objects))):
            summary["reordered_objects"] = 1
        normalized["objects"] = [object_document for _, object_document in sorted_objects]
    elif "objects" in document:
        normalized["objects"] = _deep_copy_document(objects)

    camera_document = document.get("camera")
    if camera_document is not None or "camera" in document:
        normalized["camera"] = _normalize_camera_document(camera_document, summary)

    lighting_document = document.get("lighting")
    if isinstance(lighting_document, list):
        normalized_lights = [_normalize_light_document(light_document, summary) for light_document in lighting_document]
        sorted_lights = sorted(
            enumerate(normalized_lights),
            key=lambda item: (
                0,
                item[1].get("light_id"),
            )
            if isinstance(item[1], dict) and isinstance(item[1].get("light_id"), str) and item[1].get("light_id")
            else (1, item[0]),
        )
        if [index for index, _ in sorted_lights] != list(range(len(normalized_lights))):
            summary["reordered_lights"] = 1
        normalized["lighting"] = [light_document for _, light_document in sorted_lights]
    elif "lighting" in document and lighting_document is not None:
        normalized["lighting"] = _deep_copy_document(lighting_document)

    metadata_document = document.get("metadata")
    if isinstance(metadata_document, dict):
        normalized["metadata"] = _deep_copy_document(metadata_document)
    elif "metadata" in document and metadata_document is not None:
        normalized["metadata"] = _deep_copy_document(metadata_document)

    return normalized, summary
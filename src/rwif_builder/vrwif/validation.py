from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

import yaml

VRWIF_VERSION = 1
VRWIF_REFERENCE_FRAMES = ("scene", "world")
SPATIAL_VECTOR_AXES = ("x", "y", "z")


@dataclass(frozen=True)
class VRWIFSpecValidationReport:
    spec: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)
    normalized_document: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "spec": self.spec,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }
        if self.normalized_document is not None:
            payload["normalized_document"] = dict(self.normalized_document)
        return payload


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _is_non_negative_number(value: Any) -> bool:
    return _is_number(value) and float(value) >= 0.0


def _deep_copy_document(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy_document(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy_document(item) for item in value]
    return value


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


def _validate_spatial_vector_mapping(
    value: Any,
    *,
    context: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{context} must be a mapping")
        return

    unknown_keys = sorted(key for key in value if key not in SPATIAL_VECTOR_AXES)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    for axis in SPATIAL_VECTOR_AXES:
        if not _is_number(value.get(axis)):
            errors.append(f"{context}.{axis} must be a finite number")


def _validate_trajectory_mapping(
    value: Any,
    *,
    context: str,
    errors: list[str],
    warnings: list[str],
) -> int:
    if not isinstance(value, list):
        errors.append(f"{context} must be a list")
        return 0
    if not value:
        errors.append(f"{context} must contain at least one keyframe")
        return 0

    previous_offset: float | None = None
    point_count = 0
    for index, keyframe in enumerate(value):
        keyframe_context = f"{context}[{index}]"
        if not isinstance(keyframe, dict):
            errors.append(f"{keyframe_context} must be a mapping")
            continue

        unknown_keys = sorted(key for key in keyframe if key not in {"offset_seconds", "position"})
        if unknown_keys:
            warnings.append(
                f"{keyframe_context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}"
            )

        offset_seconds = keyframe.get("offset_seconds")
        if not _is_non_negative_number(offset_seconds):
            errors.append(f"{keyframe_context}.offset_seconds must be a non-negative finite number")
        else:
            offset_value = float(offset_seconds)
            if previous_offset is not None and offset_value < previous_offset:
                errors.append(f"{context} must be sorted by non-decreasing offset_seconds")
            previous_offset = offset_value

        _validate_spatial_vector_mapping(
            keyframe.get("position"),
            context=f"{keyframe_context}.position",
            errors=errors,
            warnings=warnings,
        )
        point_count += 1
    return point_count


def _validate_object_document(
    object_document: Any,
    *,
    index: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[bool, list[str], str | None, int]:
    context = f"objects[{index}]"
    if not isinstance(object_document, dict):
        errors.append(f"{context} must be a mapping")
        return False, [], None, 0

    allowed_keys = {
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
    unknown_keys = sorted(key for key in object_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    object_id = object_document.get("object_id")
    if not isinstance(object_id, str) or not object_id:
        errors.append(f"{context}.object_id must be a non-empty string")

    object_groups_document = object_document.get("object_groups")
    groups: list[str] = []
    if not isinstance(object_groups_document, list):
        errors.append(f"{context}.object_groups must be a list")
    else:
        for group_index, group_name in enumerate(object_groups_document):
            if not isinstance(group_name, str) or not group_name:
                errors.append(f"{context}.object_groups[{group_index}] must be a non-empty string")
            else:
                groups.append(group_name)

    appearance_class = object_document.get("appearance_class", object_document.get("class"))
    if not isinstance(appearance_class, str) or not appearance_class:
        errors.append(f"{context}.appearance_class must be a non-empty string")

    _validate_spatial_vector_mapping(
        object_document.get("position"),
        context=f"{context}.position",
        errors=errors,
        warnings=warnings,
    )

    if "transform" in object_document and object_document.get("transform") is not None and not isinstance(object_document.get("transform"), dict):
        errors.append(f"{context}.transform must be a mapping")

    if "orientation" in object_document:
        _validate_spatial_vector_mapping(
            object_document.get("orientation"),
            context=f"{context}.orientation",
            errors=errors,
            warnings=warnings,
        )

    trajectory_point_count = 0
    if "trajectory" in object_document:
        trajectory_point_count = _validate_trajectory_mapping(
            object_document.get("trajectory"),
            context=f"{context}.trajectory",
            errors=errors,
            warnings=warnings,
        )

    if "metadata" in object_document and object_document.get("metadata") is not None and not isinstance(object_document.get("metadata"), dict):
        errors.append(f"{context}.metadata must be a mapping")

    return "trajectory" in object_document, groups, appearance_class if isinstance(appearance_class, str) and appearance_class else None, trajectory_point_count


def _validate_camera_document(camera_document: Any, *, errors: list[str], warnings: list[str]) -> tuple[bool, int]:
    if not isinstance(camera_document, dict):
        errors.append("camera must be a mapping")
        return False, 0

    allowed_keys = {
        "camera_id",
        "position",
        "orientation",
        "trajectory",
        "framing_intent",
        "metadata",
    }
    unknown_keys = sorted(key for key in camera_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append("camera contains unknown fields ignored by the reference builder: " + ", ".join(unknown_keys))

    camera_id = camera_document.get("camera_id")
    if not isinstance(camera_id, str) or not camera_id:
        errors.append("camera.camera_id must be a non-empty string")

    _validate_spatial_vector_mapping(
        camera_document.get("position"),
        context="camera.position",
        errors=errors,
        warnings=warnings,
    )
    _validate_spatial_vector_mapping(
        camera_document.get("orientation"),
        context="camera.orientation",
        errors=errors,
        warnings=warnings,
    )

    camera_trajectory_point_count = 0
    if "trajectory" in camera_document:
        camera_trajectory_point_count = _validate_trajectory_mapping(
            camera_document.get("trajectory"),
            context="camera.trajectory",
            errors=errors,
            warnings=warnings,
        )

    if "framing_intent" in camera_document and camera_document.get("framing_intent") is not None:
        framing_intent = camera_document.get("framing_intent")
        if not isinstance(framing_intent, str) or not framing_intent:
            errors.append("camera.framing_intent must be a non-empty string")

    if "metadata" in camera_document and camera_document.get("metadata") is not None and not isinstance(camera_document.get("metadata"), dict):
        errors.append("camera.metadata must be a mapping")

    return "trajectory" in camera_document, camera_trajectory_point_count


def _validate_lighting_document(lighting_document: Any, *, errors: list[str], warnings: list[str]) -> int:
    if not isinstance(lighting_document, list):
        errors.append("lighting must be a list")
        return 0

    light_count = 0
    for index, light_document in enumerate(lighting_document):
        context = f"lighting[{index}]"
        if not isinstance(light_document, dict):
            errors.append(f"{context} must be a mapping")
            continue

        allowed_keys = {
            "light_id",
            "position",
            "direction",
            "intensity",
            "color",
            "temperature_kelvin",
            "metadata",
        }
        unknown_keys = sorted(key for key in light_document if key not in allowed_keys)
        if unknown_keys:
            warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

        light_id = light_document.get("light_id")
        if not isinstance(light_id, str) or not light_id:
            errors.append(f"{context}.light_id must be a non-empty string")

        has_position = "position" in light_document
        has_direction = "direction" in light_document
        if not has_position and not has_direction:
            errors.append(f"{context} must define position or direction")
        if has_position:
            _validate_spatial_vector_mapping(
                light_document.get("position"),
                context=f"{context}.position",
                errors=errors,
                warnings=warnings,
            )
        if has_direction:
            _validate_spatial_vector_mapping(
                light_document.get("direction"),
                context=f"{context}.direction",
                errors=errors,
                warnings=warnings,
            )

        intensity = light_document.get("intensity")
        if not _is_non_negative_number(intensity):
            errors.append(f"{context}.intensity must be a non-negative finite number")

        if "color" in light_document and light_document.get("color") is not None:
            color = light_document.get("color")
            if not isinstance(color, str) or not color:
                errors.append(f"{context}.color must be a non-empty string")

        if "temperature_kelvin" in light_document and light_document.get("temperature_kelvin") is not None:
            if not _is_non_negative_number(light_document.get("temperature_kelvin")):
                errors.append(f"{context}.temperature_kelvin must be a non-negative finite number")

        if "metadata" in light_document and light_document.get("metadata") is not None and not isinstance(light_document.get("metadata"), dict):
            errors.append(f"{context}.metadata must be a mapping")

        light_count += 1

    return light_count


def validate_vrwif_spec(path: str | Path) -> VRWIFSpecValidationReport:
    spec_path = Path(path)
    document, load_errors = _load_spec_document(spec_path)
    if document is None:
        return VRWIFSpecValidationReport(spec=str(spec_path), is_valid=False, errors=load_errors)
    return validate_vrwif_spec_document(document, source=str(spec_path))


def validate_vrwif_spec_document(document: dict[str, Any], *, source: str = "<memory>") -> VRWIFSpecValidationReport:
    if not isinstance(document, dict):
        return VRWIFSpecValidationReport(spec=source, is_valid=False, errors=("VRWIF spec must be a mapping",))

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    allowed_keys = {
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
    unknown_keys = sorted(key for key in document if key not in allowed_keys)
    if unknown_keys:
        warnings.append("unknown top-level fields ignored by the reference builder: " + ", ".join(unknown_keys))

    vrwif_version = document.get("vrwif_version", VRWIF_VERSION)
    if vrwif_version != VRWIF_VERSION:
        errors.append(f"vrwif_version must be {VRWIF_VERSION}")

    scene_id = document.get("scene_id")
    if not isinstance(scene_id, str) or not scene_id:
        errors.append("scene_id must be a non-empty string")
    else:
        stats["scene_id"] = scene_id

    reference_frame = document.get("reference_frame")
    if not isinstance(reference_frame, str):
        errors.append("reference_frame must be a string")
    elif reference_frame not in VRWIF_REFERENCE_FRAMES:
        errors.append("reference_frame must be one of: " + ", ".join(VRWIF_REFERENCE_FRAMES))
    else:
        stats["reference_frame"] = reference_frame

    if "title" in document and not isinstance(document.get("title"), str):
        errors.append("title must be a string")
    if "description" in document and not isinstance(document.get("description"), str):
        errors.append("description must be a string")
    if "metadata" in document and document.get("metadata") is not None and not isinstance(document.get("metadata"), dict):
        errors.append("metadata must be a mapping")

    objects = document.get("objects")
    if not isinstance(objects, list):
        errors.append("objects must be a list")
        objects = []
    elif not objects:
        errors.append("objects must contain at least one object")

    objects_with_trajectory = 0
    object_trajectory_point_count = 0
    object_groups: set[str] = set()
    appearance_classes: set[str] = set()
    for index, object_document in enumerate(objects):
        has_trajectory, groups, appearance_class, trajectory_point_count = _validate_object_document(
            object_document,
            index=index,
            errors=errors,
            warnings=warnings,
        )
        if has_trajectory:
            objects_with_trajectory += 1
        object_trajectory_point_count += trajectory_point_count
        object_groups.update(groups)
        if appearance_class is not None:
            appearance_classes.add(appearance_class)

    camera_present = "camera" in document and document.get("camera") is not None
    camera_has_trajectory = False
    camera_trajectory_point_count = 0
    if camera_present:
        camera_has_trajectory, camera_trajectory_point_count = _validate_camera_document(
            document.get("camera"),
            errors=errors,
            warnings=warnings,
        )

    light_count = 0
    if "lighting" in document:
        light_count = _validate_lighting_document(document.get("lighting"), errors=errors, warnings=warnings)

    stats["object_count"] = len(objects)
    stats["objects_with_trajectory"] = objects_with_trajectory
    stats["object_trajectory_point_count"] = object_trajectory_point_count
    stats["camera_present"] = camera_present
    stats["camera_has_trajectory"] = camera_has_trajectory
    stats["camera_trajectory_point_count"] = camera_trajectory_point_count
    stats["light_count"] = light_count
    stats["object_groups"] = sorted(object_groups)
    stats["appearance_classes"] = sorted(appearance_classes)

    normalized_document = _deep_copy_document(document) if not errors else None
    return VRWIFSpecValidationReport(
        spec=source,
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
        normalized_document=normalized_document,
    )
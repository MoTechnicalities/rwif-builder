from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import yaml

from .diff import diff_vrwif_specs
from .inspect import inspect_vrwif_spec
from .normalize import normalize_vrwif_spec
from .validation import validate_vrwif_spec


def batch_validate_vrwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_object_count = 0
    total_light_count = 0

    for spec in specs:
        report = validate_vrwif_spec(Path(spec))
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_object_count += int(report.stats.get("object_count", 0))
        total_light_count += int(report.stats.get("light_count", 0))
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_object_count": total_object_count,
        "total_light_count": total_light_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate spec output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_normalize_vrwif_specs(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    report_dir: str | Path | None = None,
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    report_dir_path = Path(report_dir) if report_dir is not None else None
    output_dir_path.mkdir(parents=True, exist_ok=True)
    if report_dir_path is not None:
        report_dir_path.mkdir(parents=True, exist_ok=True)

    if format is None:
        output_suffix = ".yaml"
    elif format == "json":
        output_suffix = ".json"
    elif format == "yaml":
        output_suffix = ".yaml"
    else:
        raise ValueError("format must be yaml or json")

    results: list[dict[str, Any]] = []
    normalized_count = 0
    failed_count = 0
    total_object_count = 0
    total_light_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.normalized{output_suffix}"
        report_path = report_dir_path / f"{spec_path.stem}.normalized.report.json" if report_dir_path is not None else None
        try:
            payload = normalize_vrwif_spec(spec_path, output_path, report=report_path, format=format)
        except ValueError as exc:
            source_report = validate_vrwif_spec(spec_path)
            payload = {
                "spec": str(spec_path),
                "output": str(output_path),
                "report_output": str(report_path) if report_path is not None else None,
                "normalized": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(source_report.errors) or [str(exc)],
                "warnings": list(source_report.warnings),
                "stats": dict(source_report.stats),
            }
            failed_count += 1
        else:
            normalized_count += 1
            total_object_count += int(payload.get("normalized_object_count", 0))
            total_light_count += int(payload.get("normalized_light_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "normalized_count": normalized_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0,
        "output_dir": str(output_dir_path),
        "report_dir": str(report_dir_path) if report_dir_path is not None else None,
        "total_object_count": total_object_count,
        "total_light_count": total_light_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch normalize output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_inspect_vrwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_object_count = 0
    total_light_count = 0
    scenes_with_camera = 0

    for spec in specs:
        payload = inspect_vrwif_spec(Path(spec))
        if payload.get("is_valid", False):
            valid_count += 1
        else:
            invalid_count += 1
        total_object_count += int(payload.get("object_count", 0))
        total_light_count += len(payload.get("lighting", [])) if isinstance(payload.get("lighting"), list) else 0
        if isinstance(payload.get("camera"), dict) and payload.get("camera"):
            scenes_with_camera += 1
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_object_count": total_object_count,
        "total_light_count": total_light_count,
        "scenes_with_camera": scenes_with_camera,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch inspect output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_diff_vrwif_specs(
    left_specs: list[str | Path],
    right_specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not left_specs or not right_specs:
        raise ValueError("at least one left and one right spec must be provided")
    if len(left_specs) != len(right_specs):
        raise ValueError("left and right spec collections must have the same length")

    results: list[dict[str, Any]] = []
    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    total_metadata_fields_changed = 0
    total_changed_objects = 0

    for pair_index, (left_spec, right_spec) in enumerate(zip(left_specs, right_specs, strict=True)):
        payload = diff_vrwif_specs(left_spec, right_spec)
        payload["pair_index"] = pair_index

        summary = payload.get("change_summary", {})
        metadata_fields_changed = int(summary.get("metadata_fields_changed", 0))
        changed_objects = int(summary.get("changed_objects", 0))

        pair_changed = _infer_pair_changed(payload)
        payload["pair_changed"] = pair_changed

        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not payload.get("left_valid", False) or not payload.get("right_valid", False):
            invalid_pairs += 1

        total_metadata_fields_changed += metadata_fields_changed
        total_changed_objects += changed_objects
        results.append(payload)

    payload = {
        "pairs_compared": len(results),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "is_valid": invalid_pairs == 0,
        "total_metadata_fields_changed": total_metadata_fields_changed,
        "total_changed_objects": total_changed_objects,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch diff output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def analyze_batch_diff_report(
    input_path: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    report_path = Path(input_path)
    report_document = _load_auxiliary_document(report_path, label="batch diff analysis input")
    analysis_payload = _analyze_batch_diff_payload(report_document, analysis_input=str(report_path))

    if output is not None:
        analysis_output_path = Path(output)
        report_format = _resolve_auxiliary_format(analysis_output_path, label="batch diff analysis output")
        _write_auxiliary_document(analysis_output_path, analysis_payload, report_format)
        analysis_payload["report_output"] = str(analysis_output_path)
        analysis_payload["report_format"] = report_format

    return analysis_payload


def batch_review_vrwif_specs(
    left_specs: list[str | Path],
    right_specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    diff_payload = batch_diff_vrwif_specs(left_specs, right_specs)
    analysis_payload = _analyze_batch_diff_payload(diff_payload)

    review_payload = {
        "pairs_compared": diff_payload["pairs_compared"],
        "changed_pairs": diff_payload["changed_pairs"],
        "unchanged_pairs": diff_payload["unchanged_pairs"],
        "invalid_pairs": diff_payload["invalid_pairs"],
        "is_valid": diff_payload["is_valid"] and analysis_payload["is_valid"],
        "diff_report": diff_payload,
        "analysis": analysis_payload,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch review output")
        _write_auxiliary_document(output_path, review_payload, report_format)
        review_payload["report_output"] = str(output_path)
        review_payload["report_format"] = report_format

    return review_payload


def _analyze_batch_diff_payload(report_document: dict[str, Any], *, analysis_input: str | None = None) -> dict[str, Any]:
    results = report_document.get("results")
    if not isinstance(results, list):
        raise ValueError("batch diff analysis input must contain a 'results' list")

    metadata_counter: Counter[str] = Counter()
    changed_object_counter: Counter[str] = Counter()
    added_object_counter: Counter[str] = Counter()
    removed_object_counter: Counter[str] = Counter()
    metadata_pair_indexes: dict[str, list[int]] = {}
    changed_object_pair_indexes: dict[str, list[int]] = {}
    added_object_pair_indexes: dict[str, list[int]] = {}
    removed_object_pair_indexes: dict[str, list[int]] = {}

    reference_frame_changed_pairs = 0
    object_groups_changed_pairs = 0
    appearance_classes_changed_pairs = 0
    positioned_object_delta_pairs = 0
    total_positioned_objects_delta = 0
    orientation_delta_pairs = 0
    total_objects_with_orientation_delta = 0
    trajectory_delta_pairs = 0
    total_objects_with_trajectory_delta = 0
    trajectory_point_delta_pairs = 0
    total_object_trajectory_point_delta = 0
    camera_changed_pairs = 0
    camera_trajectory_changed_pairs = 0
    light_count_delta_pairs = 0
    total_light_count_delta = 0
    light_ids_changed_pairs = 0

    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0

    for index, raw_result in enumerate(results):
        if not isinstance(raw_result, dict):
            continue

        pair_index = int(raw_result.get("pair_index", index))
        pair_changed = bool(raw_result.get("pair_changed", _infer_pair_changed(raw_result)))
        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not raw_result.get("left_valid", False) or not raw_result.get("right_valid", False):
            invalid_pairs += 1

        metadata_changes = raw_result.get("metadata_changes")
        if isinstance(metadata_changes, dict):
            for field in metadata_changes:
                field_name = str(field)
                metadata_counter[field_name] += 1
                metadata_pair_indexes.setdefault(field_name, []).append(pair_index)

        for object_name in _string_list(raw_result.get("changed_objects")):
            changed_object_counter[object_name] += 1
            changed_object_pair_indexes.setdefault(object_name, []).append(pair_index)

        for object_name in _string_list(raw_result.get("added_objects")):
            added_object_counter[object_name] += 1
            added_object_pair_indexes.setdefault(object_name, []).append(pair_index)

        for object_name in _string_list(raw_result.get("removed_objects")):
            removed_object_counter[object_name] += 1
            removed_object_pair_indexes.setdefault(object_name, []).append(pair_index)

        scene_changes = raw_result.get("scene_changes")
        if isinstance(scene_changes, dict):
            if bool(scene_changes.get("reference_frame_changed", False)):
                reference_frame_changed_pairs += 1
            if bool(scene_changes.get("object_groups_changed", False)):
                object_groups_changed_pairs += 1
            if bool(scene_changes.get("appearance_classes_changed", False)):
                appearance_classes_changed_pairs += 1

            positioned_delta = int(scene_changes.get("positioned_objects_delta", 0) or 0)
            total_positioned_objects_delta += positioned_delta
            if positioned_delta != 0:
                positioned_object_delta_pairs += 1

            orientation_delta = int(scene_changes.get("objects_with_orientation_delta", 0) or 0)
            total_objects_with_orientation_delta += orientation_delta
            if orientation_delta != 0:
                orientation_delta_pairs += 1

            trajectory_delta = int(scene_changes.get("objects_with_trajectory_delta", 0) or 0)
            total_objects_with_trajectory_delta += trajectory_delta
            if trajectory_delta != 0:
                trajectory_delta_pairs += 1

            trajectory_point_delta = int(scene_changes.get("object_trajectory_point_count_delta", 0) or 0)
            total_object_trajectory_point_delta += trajectory_point_delta
            if trajectory_point_delta != 0:
                trajectory_point_delta_pairs += 1

            if bool(scene_changes.get("camera_changed", False)):
                camera_changed_pairs += 1
            if bool(scene_changes.get("camera_trajectory_changed", False)):
                camera_trajectory_changed_pairs += 1

            light_count_delta = int(scene_changes.get("light_count_delta", 0) or 0)
            total_light_count_delta += light_count_delta
            if light_count_delta != 0:
                light_count_delta_pairs += 1

            if bool(scene_changes.get("light_ids_changed", False)):
                light_ids_changed_pairs += 1

    pairs_compared = int(report_document.get("pairs_compared", len(results)))
    analysis_payload = {
        "pairs_compared": pairs_compared,
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "is_valid": invalid_pairs == 0,
        "metadata_field_frequencies": _rank_frequency_items(metadata_counter, metadata_pair_indexes, "field", changed_pairs),
        "changed_object_frequencies": _rank_frequency_items(changed_object_counter, changed_object_pair_indexes, "object", changed_pairs),
        "added_object_frequencies": _rank_frequency_items(added_object_counter, added_object_pair_indexes, "object", changed_pairs),
        "removed_object_frequencies": _rank_frequency_items(removed_object_counter, removed_object_pair_indexes, "object", changed_pairs),
        "objects_changed_in_all_changed_pairs": _universal_items(changed_object_counter, changed_pairs),
        "metadata_fields_changed_in_all_changed_pairs": _universal_items(metadata_counter, changed_pairs),
        "objects_added_in_all_changed_pairs": _universal_items(added_object_counter, changed_pairs),
        "objects_removed_in_all_changed_pairs": _universal_items(removed_object_counter, changed_pairs),
        "scene_change_summary": {
            "reference_frame_changed_pairs": reference_frame_changed_pairs,
            "object_groups_changed_pairs": object_groups_changed_pairs,
            "appearance_classes_changed_pairs": appearance_classes_changed_pairs,
            "pairs_with_positioned_object_delta": positioned_object_delta_pairs,
            "total_positioned_objects_delta": total_positioned_objects_delta,
            "pairs_with_orientation_delta": orientation_delta_pairs,
            "total_objects_with_orientation_delta": total_objects_with_orientation_delta,
            "pairs_with_trajectory_delta": trajectory_delta_pairs,
            "total_objects_with_trajectory_delta": total_objects_with_trajectory_delta,
            "pairs_with_trajectory_point_delta": trajectory_point_delta_pairs,
            "total_object_trajectory_point_delta": total_object_trajectory_point_delta,
            "camera_changed_pairs": camera_changed_pairs,
            "camera_trajectory_changed_pairs": camera_trajectory_changed_pairs,
            "pairs_with_light_count_delta": light_count_delta_pairs,
            "total_light_count_delta": total_light_count_delta,
            "light_ids_changed_pairs": light_ids_changed_pairs,
        },
    }

    if analysis_input is not None:
        analysis_payload["analysis_input"] = analysis_input

    return analysis_payload


def _infer_pair_changed(result: dict[str, Any]) -> bool:
    summary = result.get("change_summary")
    if isinstance(summary, dict) and any(
        int(summary.get(key, 0) or 0)
        for key in ("metadata_fields_changed", "added_objects", "removed_objects", "changed_objects")
    ):
        return True

    scene_changes = result.get("scene_changes")
    if isinstance(scene_changes, dict):
        if any(
            bool(scene_changes.get(key, False))
            for key in (
                "reference_frame_changed",
                "object_groups_changed",
                "appearance_classes_changed",
                "camera_changed",
                "camera_trajectory_changed",
                "light_ids_changed",
            )
        ):
            return True
        if any(
            int(scene_changes.get(key, 0) or 0) != 0
            for key in (
                "positioned_objects_delta",
                "objects_with_orientation_delta",
                "objects_with_trajectory_delta",
                "object_trajectory_point_count_delta",
                "light_count_delta",
            )
        ):
            return True

    return False


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _rank_frequency_items(
    counter: Counter[str],
    pair_indexes: dict[str, list[int]],
    label: str,
    changed_pairs: int,
) -> list[dict[str, Any]]:
    denominator = changed_pairs if changed_pairs > 0 else 1
    ranked: list[dict[str, Any]] = []
    for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        ranked.append(
            {
                label: name,
                "pairs_changed": count,
                "pair_indexes": pair_indexes.get(name, []),
                "frequency": count / denominator,
            }
        )
    return ranked


def _universal_items(counter: Counter[str], changed_pairs: int) -> list[str]:
    if changed_pairs == 0:
        return []
    return sorted(name for name, count in counter.items() if count == changed_pairs)


def _resolve_auxiliary_format(output_path: Path, *, label: str) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError(f"could not infer {label} format from path; use a .json, .yaml, or .yml suffix")


def _load_auxiliary_document(input_path: Path, *, label: str) -> dict[str, Any]:
    document_format = _resolve_auxiliary_format(input_path, label=label)
    raw_text = input_path.read_text(encoding="utf-8")
    if document_format == "json":
        document = json.loads(raw_text)
    else:
        document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise ValueError(f"{label} must decode to a top-level mapping")
    return document


def _write_auxiliary_document(output_path: Path, document: dict[str, Any], report_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
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
    assumptions_dir: str | Path | None = None,
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    report_dir_path = Path(report_dir) if report_dir is not None else None
    assumptions_dir_path = Path(assumptions_dir) if assumptions_dir is not None else None
    output_dir_path.mkdir(parents=True, exist_ok=True)
    if report_dir_path is not None:
        report_dir_path.mkdir(parents=True, exist_ok=True)
    if assumptions_dir_path is not None:
        assumptions_dir_path.mkdir(parents=True, exist_ok=True)

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
    total_assumption_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.normalized{output_suffix}"
        report_path = report_dir_path / f"{spec_path.stem}.normalized.report.json" if report_dir_path is not None else None
        assumptions_path = (
            assumptions_dir_path / f"{spec_path.stem}.normalized.assumptions.json"
            if assumptions_dir_path is not None
            else None
        )
        try:
            payload = normalize_vrwif_spec(
                spec_path,
                output_path,
                report=report_path,
                assumptions=assumptions_path,
                format=format,
            )
        except ValueError as exc:
            source_report = validate_vrwif_spec(spec_path)
            payload = {
                "spec": str(spec_path),
                "output": str(output_path),
                "report_output": str(report_path) if report_path is not None else None,
                "assumptions_output": str(assumptions_path) if assumptions_path is not None else None,
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
            total_assumption_count += int(payload.get("assumption_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "normalized_count": normalized_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0,
        "output_dir": str(output_dir_path),
        "report_dir": str(report_dir_path) if report_dir_path is not None else None,
        "assumptions_dir": str(assumptions_dir_path) if assumptions_dir_path is not None else None,
        "total_object_count": total_object_count,
        "total_light_count": total_light_count,
        "total_assumption_count": total_assumption_count,
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


def analyze_batch_normalize_report(
    input_path: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    report_path = Path(input_path)
    report_document = _load_auxiliary_document(report_path, label="batch normalize analysis input")
    analysis_payload = _analyze_batch_normalize_payload(report_document, analysis_input=str(report_path))

    if output is not None:
        analysis_output_path = Path(output)
        report_format = _resolve_auxiliary_format(analysis_output_path, label="batch normalize analysis output")
        _write_auxiliary_document(analysis_output_path, analysis_payload, report_format)
        analysis_payload["report_output"] = str(analysis_output_path)
        analysis_payload["report_format"] = report_format

    return analysis_payload


def batch_normalize_review_vrwif_specs(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    report_dir: str | Path | None = None,
    assumptions_dir: str | Path | None = None,
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    normalize_payload = batch_normalize_vrwif_specs(
        specs,
        output_dir,
        report_dir=report_dir,
        assumptions_dir=assumptions_dir,
        format=format,
    )
    analysis_payload = _analyze_batch_normalize_payload(normalize_payload)

    review_payload = {
        "specs_processed": normalize_payload["specs_processed"],
        "normalized_count": normalize_payload["normalized_count"],
        "failed_count": normalize_payload["failed_count"],
        "is_valid": normalize_payload["is_valid"] and analysis_payload["is_valid"],
        "normalize_report": normalize_payload,
        "analysis": analysis_payload,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch normalize review output")
        _write_auxiliary_document(output_path, review_payload, report_format)
        review_payload["report_output"] = str(output_path)
        review_payload["report_format"] = report_format

    return review_payload


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


def _analyze_batch_normalize_payload(report_document: dict[str, Any], *, analysis_input: str | None = None) -> dict[str, Any]:
    results = report_document.get("results")
    if not isinstance(results, list):
        raise ValueError("batch normalize analysis input must contain a 'results' list")

    action_spec_counter: Counter[str] = Counter()
    action_total_counter: Counter[str] = Counter()
    action_spec_indexes: dict[str, list[int]] = {}
    action_specs: dict[str, list[str]] = {}
    source_error_counter: Counter[str] = Counter()
    source_error_indexes: dict[str, list[int]] = {}
    source_error_specs: dict[str, list[str]] = {}
    source_warning_counter: Counter[str] = Counter()
    source_warning_indexes: dict[str, list[int]] = {}
    source_warning_specs: dict[str, list[str]] = {}
    normalized_warning_counter: Counter[str] = Counter()
    normalized_warning_indexes: dict[str, list[int]] = {}
    normalized_warning_specs: dict[str, list[str]] = {}

    normalized_count = 0
    failed_count = 0
    specs_with_assumptions = 0
    specs_with_source_errors = 0
    specs_with_source_warnings = 0
    specs_with_normalized_warnings = 0

    top_specs: list[dict[str, Any]] = []

    for index, raw_result in enumerate(results):
        if not isinstance(raw_result, dict):
            continue

        spec_index = index
        spec_name = str(raw_result.get("spec", f"<spec {index}>"))
        normalized = bool(raw_result.get("normalized", False))

        if normalized:
            normalized_count += 1
        else:
            failed_count += 1

        source_errors = _string_list(raw_result.get("source_errors") or raw_result.get("errors"))
        source_warnings = _string_list(raw_result.get("source_warnings") or raw_result.get("warnings"))
        normalized_warnings = _string_list(raw_result.get("normalized_spec_warnings"))

        if source_errors:
            specs_with_source_errors += 1
        if source_warnings:
            specs_with_source_warnings += 1
        if normalized_warnings:
            specs_with_normalized_warnings += 1

        normalization_summary = raw_result.get("normalization_summary")
        actions_triggered: list[str] = []
        if isinstance(normalization_summary, dict):
            for action_name, raw_count in normalization_summary.items():
                count = int(raw_count or 0)
                if count <= 0:
                    continue
                action_key = str(action_name)
                actions_triggered.append(action_key)
                action_spec_counter[action_key] += 1
                action_total_counter[action_key] += count
                action_spec_indexes.setdefault(action_key, []).append(spec_index)
                action_specs.setdefault(action_key, []).append(spec_name)

        assumption_count = _estimate_assumption_count(
            raw_result,
            normalization_summary if isinstance(normalization_summary, dict) else None,
            source_warnings,
            normalized_warnings,
        )
        if assumption_count > 0:
            specs_with_assumptions += 1

        for message in source_errors:
            source_error_counter[message] += 1
            source_error_indexes.setdefault(message, []).append(spec_index)
            source_error_specs.setdefault(message, []).append(spec_name)

        for message in source_warnings:
            source_warning_counter[message] += 1
            source_warning_indexes.setdefault(message, []).append(spec_index)
            source_warning_specs.setdefault(message, []).append(spec_name)

        for message in normalized_warnings:
            normalized_warning_counter[message] += 1
            normalized_warning_indexes.setdefault(message, []).append(spec_index)
            normalized_warning_specs.setdefault(message, []).append(spec_name)

        top_specs.append(
            {
                "spec": spec_name,
                "spec_index": spec_index,
                "normalized": normalized,
                "assumption_count": assumption_count,
                "source_error_count": len(source_errors),
                "source_warning_count": len(source_warnings),
                "normalized_warning_count": len(normalized_warnings),
                "actions_triggered": sorted(actions_triggered),
            }
        )

    top_specs.sort(
        key=lambda item: (
            -int(item.get("assumption_count", 0)),
            -len(item.get("actions_triggered", [])),
            -int(item.get("source_error_count", 0)),
            str(item.get("spec", "")),
        )
    )

    analysis_payload = {
        "specs_processed": int(report_document.get("specs_processed", len(results))),
        "normalized_count": normalized_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0,
        "normalization_action_frequencies": _rank_normalization_items(
            action_spec_counter,
            action_total_counter,
            action_spec_indexes,
            action_specs,
            normalized_count,
        ),
        "actions_present_in_all_normalized_specs": _universal_items(action_spec_counter, normalized_count),
        "source_error_frequencies": _rank_message_items(
            source_error_counter,
            source_error_indexes,
            source_error_specs,
            "error",
            len(results),
        ),
        "source_warning_frequencies": _rank_message_items(
            source_warning_counter,
            source_warning_indexes,
            source_warning_specs,
            "warning",
            len(results),
        ),
        "normalized_warning_frequencies": _rank_message_items(
            normalized_warning_counter,
            normalized_warning_indexes,
            normalized_warning_specs,
            "warning",
            normalized_count,
        ),
        "summary": {
            "specs_with_assumptions": specs_with_assumptions,
            "specs_with_source_errors": specs_with_source_errors,
            "specs_with_source_warnings": specs_with_source_warnings,
            "specs_with_normalized_warnings": specs_with_normalized_warnings,
        },
        "top_specs_by_assumption_count": top_specs[:10],
    }

    if analysis_input is not None:
        analysis_payload["analysis_input"] = analysis_input

    return analysis_payload


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
    object_ids_changed_pairs = 0
    object_ids_count_delta_pairs = 0
    total_object_ids_count_delta = 0
    object_groups_changed_pairs = 0
    object_groups_count_delta_pairs = 0
    total_object_groups_count_delta = 0
    appearance_classes_changed_pairs = 0
    object_states_changed_pairs = 0
    object_visibilities_changed_pairs = 0
    object_count_delta_pairs = 0
    total_object_count_delta = 0
    object_distance_delta_pairs = 0
    total_object_distance_delta = 0.0
    object_distance_range_changed_pairs = 0
    positioned_object_delta_pairs = 0
    total_positioned_objects_delta = 0
    orientation_delta_pairs = 0
    total_objects_with_orientation_delta = 0
    trajectory_delta_pairs = 0
    total_objects_with_trajectory_delta = 0
    trajectory_duration_delta_pairs = 0
    total_object_trajectory_duration_delta = 0.0
    trajectory_duration_range_changed_pairs = 0
    trajectory_path_length_delta_pairs = 0
    total_object_trajectory_path_length_delta = 0.0
    trajectory_path_length_range_changed_pairs = 0
    trajectory_displacement_delta_pairs = 0
    total_object_trajectory_displacement_delta = 0.0
    trajectory_displacement_range_changed_pairs = 0
    trajectory_average_speed_delta_pairs = 0
    total_object_trajectory_average_speed_delta = 0.0
    trajectory_average_speed_range_changed_pairs = 0
    trajectory_peak_speed_delta_pairs = 0
    total_object_trajectory_peak_speed_delta = 0.0
    trajectory_peak_speed_range_changed_pairs = 0
    trajectory_speed_standard_deviation_delta_pairs = 0
    total_object_trajectory_speed_standard_deviation_delta = 0.0
    trajectory_speed_standard_deviation_range_changed_pairs = 0
    trajectory_average_acceleration_delta_pairs = 0
    total_object_trajectory_average_acceleration_delta = 0.0
    trajectory_average_acceleration_range_changed_pairs = 0
    trajectory_peak_acceleration_delta_pairs = 0
    total_object_trajectory_peak_acceleration_delta = 0.0
    trajectory_peak_acceleration_range_changed_pairs = 0
    trajectory_straightness_delta_pairs = 0
    total_object_trajectory_straightness_delta = 0.0
    trajectory_straightness_range_changed_pairs = 0
    trajectory_turn_angle_delta_pairs = 0
    total_object_trajectory_turn_angle_delta_degrees = 0.0
    trajectory_turn_angle_range_changed_pairs = 0
    trajectory_peak_turn_angle_delta_pairs = 0
    total_object_trajectory_peak_turn_angle_delta_degrees = 0.0
    trajectory_peak_turn_angle_range_changed_pairs = 0
    trajectory_turn_count_delta_pairs = 0
    total_object_trajectory_turn_count_delta = 0
    trajectory_turn_count_range_changed_pairs = 0
    trajectory_average_turn_angle_delta_pairs = 0
    total_object_trajectory_average_turn_angle_delta_degrees = 0.0
    trajectory_average_turn_angle_range_changed_pairs = 0
    trajectory_turn_angle_standard_deviation_delta_pairs = 0
    total_object_trajectory_turn_angle_standard_deviation_delta_degrees = 0.0
    trajectory_turn_angle_standard_deviation_range_changed_pairs = 0
    trajectory_point_delta_pairs = 0
    total_object_trajectory_point_delta = 0
    camera_changed_pairs = 0
    camera_distance_delta_pairs = 0
    total_camera_distance_delta = 0.0
    camera_trajectory_duration_delta_pairs = 0
    total_camera_trajectory_duration_delta = 0.0
    camera_trajectory_path_length_delta_pairs = 0
    total_camera_trajectory_path_length_delta = 0.0
    camera_trajectory_displacement_delta_pairs = 0
    total_camera_trajectory_displacement_delta = 0.0
    camera_trajectory_average_speed_delta_pairs = 0
    total_camera_trajectory_average_speed_delta = 0.0
    camera_trajectory_peak_speed_delta_pairs = 0
    total_camera_trajectory_peak_speed_delta = 0.0
    camera_trajectory_speed_standard_deviation_delta_pairs = 0
    total_camera_trajectory_speed_standard_deviation_delta = 0.0
    camera_trajectory_average_acceleration_delta_pairs = 0
    total_camera_trajectory_average_acceleration_delta = 0.0
    camera_trajectory_peak_acceleration_delta_pairs = 0
    total_camera_trajectory_peak_acceleration_delta = 0.0
    camera_trajectory_straightness_delta_pairs = 0
    total_camera_trajectory_straightness_delta = 0.0
    camera_trajectory_turn_angle_delta_pairs = 0
    total_camera_trajectory_turn_angle_delta_degrees = 0.0
    camera_trajectory_peak_turn_angle_delta_pairs = 0
    total_camera_trajectory_peak_turn_angle_delta_degrees = 0.0
    camera_trajectory_turn_count_delta_pairs = 0
    total_camera_trajectory_turn_count_delta = 0
    camera_trajectory_average_turn_angle_delta_pairs = 0
    total_camera_trajectory_average_turn_angle_delta_degrees = 0.0
    camera_trajectory_turn_angle_standard_deviation_delta_pairs = 0
    total_camera_trajectory_turn_angle_standard_deviation_delta_degrees = 0.0
    camera_trajectory_point_delta_pairs = 0
    total_camera_trajectory_point_delta = 0
    camera_present_changed_pairs = 0
    framing_intent_changed_pairs = 0
    camera_id_changed_pairs = 0
    camera_has_trajectory_changed_pairs = 0
    camera_trajectory_changed_pairs = 0
    lighting_present_changed_pairs = 0
    light_count_delta_pairs = 0
    total_light_count_delta = 0
    light_intensity_total_delta_pairs = 0
    total_light_intensity_delta = 0.0
    light_intensity_range_changed_pairs = 0
    positioned_light_delta_pairs = 0
    total_positioned_lights_delta = 0
    directional_light_delta_pairs = 0
    total_directional_lights_delta = 0
    light_temperature_delta_pairs = 0
    total_lights_with_temperature_delta = 0
    light_temperature_range_changed_pairs = 0
    light_colors_changed_pairs = 0
    light_ids_changed_pairs = 0
    light_ids_count_delta_pairs = 0
    total_light_ids_count_delta = 0

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
            if bool(scene_changes.get("object_ids_changed", False)):
                object_ids_changed_pairs += 1
            object_ids_count_delta = int(scene_changes.get("object_ids_count_delta", 0) or 0)
            total_object_ids_count_delta += object_ids_count_delta
            if object_ids_count_delta != 0:
                object_ids_count_delta_pairs += 1
            if bool(scene_changes.get("object_groups_changed", False)):
                object_groups_changed_pairs += 1
            object_groups_count_delta = int(scene_changes.get("object_groups_count_delta", 0) or 0)
            total_object_groups_count_delta += object_groups_count_delta
            if object_groups_count_delta != 0:
                object_groups_count_delta_pairs += 1
            if bool(scene_changes.get("appearance_classes_changed", False)):
                appearance_classes_changed_pairs += 1
            if bool(scene_changes.get("object_states_changed", False)):
                object_states_changed_pairs += 1
            if bool(scene_changes.get("object_visibilities_changed", False)):
                object_visibilities_changed_pairs += 1

            object_count_delta = int(scene_changes.get("object_count_delta", 0) or 0)
            total_object_count_delta += object_count_delta
            if object_count_delta != 0:
                object_count_delta_pairs += 1

            object_distance_delta = float(scene_changes.get("object_distance_from_origin_total_delta", 0.0) or 0.0)
            total_object_distance_delta += object_distance_delta
            if object_distance_delta != 0.0:
                object_distance_delta_pairs += 1

            if bool(scene_changes.get("object_distance_from_origin_range_changed", False)):
                object_distance_range_changed_pairs += 1

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

            trajectory_duration_delta = float(scene_changes.get("object_trajectory_duration_total_delta", 0.0) or 0.0)
            total_object_trajectory_duration_delta += trajectory_duration_delta
            if trajectory_duration_delta != 0.0:
                trajectory_duration_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_duration_range_changed", False)):
                trajectory_duration_range_changed_pairs += 1

            trajectory_path_length_delta = float(scene_changes.get("object_trajectory_path_length_total_delta", 0.0) or 0.0)
            total_object_trajectory_path_length_delta += trajectory_path_length_delta
            if trajectory_path_length_delta != 0.0:
                trajectory_path_length_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_path_length_range_changed", False)):
                trajectory_path_length_range_changed_pairs += 1

            trajectory_displacement_delta = float(scene_changes.get("object_trajectory_displacement_total_delta", 0.0) or 0.0)
            total_object_trajectory_displacement_delta += trajectory_displacement_delta
            if trajectory_displacement_delta != 0.0:
                trajectory_displacement_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_displacement_range_changed", False)):
                trajectory_displacement_range_changed_pairs += 1

            trajectory_average_speed_delta = float(scene_changes.get("object_trajectory_average_speed_total_delta", 0.0) or 0.0)
            total_object_trajectory_average_speed_delta += trajectory_average_speed_delta
            if trajectory_average_speed_delta != 0.0:
                trajectory_average_speed_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_average_speed_range_changed", False)):
                trajectory_average_speed_range_changed_pairs += 1

            trajectory_peak_speed_delta = float(scene_changes.get("object_trajectory_peak_speed_total_delta", 0.0) or 0.0)
            total_object_trajectory_peak_speed_delta += trajectory_peak_speed_delta
            if trajectory_peak_speed_delta != 0.0:
                trajectory_peak_speed_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_peak_speed_range_changed", False)):
                trajectory_peak_speed_range_changed_pairs += 1

            trajectory_speed_standard_deviation_delta = float(
                scene_changes.get("object_trajectory_speed_standard_deviation_total_delta", 0.0) or 0.0
            )
            total_object_trajectory_speed_standard_deviation_delta += trajectory_speed_standard_deviation_delta
            if trajectory_speed_standard_deviation_delta != 0.0:
                trajectory_speed_standard_deviation_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_speed_standard_deviation_range_changed", False)):
                trajectory_speed_standard_deviation_range_changed_pairs += 1

            trajectory_average_acceleration_delta = float(
                scene_changes.get("object_trajectory_average_acceleration_total_delta", 0.0) or 0.0
            )
            total_object_trajectory_average_acceleration_delta += trajectory_average_acceleration_delta
            if trajectory_average_acceleration_delta != 0.0:
                trajectory_average_acceleration_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_average_acceleration_range_changed", False)):
                trajectory_average_acceleration_range_changed_pairs += 1

            trajectory_peak_acceleration_delta = float(
                scene_changes.get("object_trajectory_peak_acceleration_total_delta", 0.0) or 0.0
            )
            total_object_trajectory_peak_acceleration_delta += trajectory_peak_acceleration_delta
            if trajectory_peak_acceleration_delta != 0.0:
                trajectory_peak_acceleration_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_peak_acceleration_range_changed", False)):
                trajectory_peak_acceleration_range_changed_pairs += 1

            trajectory_straightness_delta = float(scene_changes.get("object_trajectory_straightness_total_delta", 0.0) or 0.0)
            total_object_trajectory_straightness_delta += trajectory_straightness_delta
            if trajectory_straightness_delta != 0.0:
                trajectory_straightness_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_straightness_range_changed", False)):
                trajectory_straightness_range_changed_pairs += 1

            trajectory_turn_angle_delta = float(scene_changes.get("object_trajectory_turn_angle_total_degrees_delta", 0.0) or 0.0)
            total_object_trajectory_turn_angle_delta_degrees += trajectory_turn_angle_delta
            if trajectory_turn_angle_delta != 0.0:
                trajectory_turn_angle_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_turn_angle_range_degrees_changed", False)):
                trajectory_turn_angle_range_changed_pairs += 1

            trajectory_peak_turn_angle_delta = float(scene_changes.get("object_trajectory_peak_turn_angle_total_degrees_delta", 0.0) or 0.0)
            total_object_trajectory_peak_turn_angle_delta_degrees += trajectory_peak_turn_angle_delta
            if trajectory_peak_turn_angle_delta != 0.0:
                trajectory_peak_turn_angle_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_peak_turn_angle_range_degrees_changed", False)):
                trajectory_peak_turn_angle_range_changed_pairs += 1

            trajectory_turn_count_delta = int(scene_changes.get("object_trajectory_turn_count_total_delta", 0) or 0)
            total_object_trajectory_turn_count_delta += trajectory_turn_count_delta
            if trajectory_turn_count_delta != 0:
                trajectory_turn_count_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_turn_count_range_changed", False)):
                trajectory_turn_count_range_changed_pairs += 1

            trajectory_average_turn_angle_delta = float(scene_changes.get("object_trajectory_average_turn_angle_total_degrees_delta", 0.0) or 0.0)
            total_object_trajectory_average_turn_angle_delta_degrees += trajectory_average_turn_angle_delta
            if trajectory_average_turn_angle_delta != 0.0:
                trajectory_average_turn_angle_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_average_turn_angle_range_degrees_changed", False)):
                trajectory_average_turn_angle_range_changed_pairs += 1

            trajectory_turn_angle_standard_deviation_delta = float(
                scene_changes.get("object_trajectory_turn_angle_standard_deviation_total_degrees_delta", 0.0) or 0.0
            )
            total_object_trajectory_turn_angle_standard_deviation_delta_degrees += trajectory_turn_angle_standard_deviation_delta
            if trajectory_turn_angle_standard_deviation_delta != 0.0:
                trajectory_turn_angle_standard_deviation_delta_pairs += 1

            if bool(scene_changes.get("object_trajectory_turn_angle_standard_deviation_range_degrees_changed", False)):
                trajectory_turn_angle_standard_deviation_range_changed_pairs += 1

            trajectory_point_delta = int(scene_changes.get("object_trajectory_point_count_delta", 0) or 0)
            total_object_trajectory_point_delta += trajectory_point_delta
            if trajectory_point_delta != 0:
                trajectory_point_delta_pairs += 1

            if bool(scene_changes.get("camera_changed", False)):
                camera_changed_pairs += 1

            camera_distance_delta = float(scene_changes.get("camera_distance_from_origin_delta", 0.0) or 0.0)
            total_camera_distance_delta += camera_distance_delta
            if camera_distance_delta != 0.0:
                camera_distance_delta_pairs += 1

            camera_trajectory_duration_delta = float(scene_changes.get("camera_trajectory_duration_delta", 0.0) or 0.0)
            total_camera_trajectory_duration_delta += camera_trajectory_duration_delta
            if camera_trajectory_duration_delta != 0.0:
                camera_trajectory_duration_delta_pairs += 1

            camera_trajectory_path_length_delta = float(scene_changes.get("camera_trajectory_path_length_delta", 0.0) or 0.0)
            total_camera_trajectory_path_length_delta += camera_trajectory_path_length_delta
            if camera_trajectory_path_length_delta != 0.0:
                camera_trajectory_path_length_delta_pairs += 1

            camera_trajectory_displacement_delta = float(scene_changes.get("camera_trajectory_displacement_delta", 0.0) or 0.0)
            total_camera_trajectory_displacement_delta += camera_trajectory_displacement_delta
            if camera_trajectory_displacement_delta != 0.0:
                camera_trajectory_displacement_delta_pairs += 1

            camera_trajectory_average_speed_delta = float(scene_changes.get("camera_trajectory_average_speed_delta", 0.0) or 0.0)
            total_camera_trajectory_average_speed_delta += camera_trajectory_average_speed_delta
            if camera_trajectory_average_speed_delta != 0.0:
                camera_trajectory_average_speed_delta_pairs += 1

            camera_trajectory_peak_speed_delta = float(scene_changes.get("camera_trajectory_peak_speed_delta", 0.0) or 0.0)
            total_camera_trajectory_peak_speed_delta += camera_trajectory_peak_speed_delta
            if camera_trajectory_peak_speed_delta != 0.0:
                camera_trajectory_peak_speed_delta_pairs += 1

            camera_trajectory_speed_standard_deviation_delta = float(
                scene_changes.get("camera_trajectory_speed_standard_deviation_delta", 0.0) or 0.0
            )
            total_camera_trajectory_speed_standard_deviation_delta += camera_trajectory_speed_standard_deviation_delta
            if camera_trajectory_speed_standard_deviation_delta != 0.0:
                camera_trajectory_speed_standard_deviation_delta_pairs += 1

            camera_trajectory_average_acceleration_delta = float(
                scene_changes.get("camera_trajectory_average_acceleration_delta", 0.0) or 0.0
            )
            total_camera_trajectory_average_acceleration_delta += camera_trajectory_average_acceleration_delta
            if camera_trajectory_average_acceleration_delta != 0.0:
                camera_trajectory_average_acceleration_delta_pairs += 1

            camera_trajectory_peak_acceleration_delta = float(
                scene_changes.get("camera_trajectory_peak_acceleration_delta", 0.0) or 0.0
            )
            total_camera_trajectory_peak_acceleration_delta += camera_trajectory_peak_acceleration_delta
            if camera_trajectory_peak_acceleration_delta != 0.0:
                camera_trajectory_peak_acceleration_delta_pairs += 1

            camera_trajectory_straightness_delta = float(scene_changes.get("camera_trajectory_straightness_delta", 0.0) or 0.0)
            total_camera_trajectory_straightness_delta += camera_trajectory_straightness_delta
            if camera_trajectory_straightness_delta != 0.0:
                camera_trajectory_straightness_delta_pairs += 1

            camera_trajectory_turn_angle_delta = float(scene_changes.get("camera_trajectory_turn_angle_degrees_delta", 0.0) or 0.0)
            total_camera_trajectory_turn_angle_delta_degrees += camera_trajectory_turn_angle_delta
            if camera_trajectory_turn_angle_delta != 0.0:
                camera_trajectory_turn_angle_delta_pairs += 1

            camera_trajectory_peak_turn_angle_delta = float(scene_changes.get("camera_trajectory_peak_turn_angle_degrees_delta", 0.0) or 0.0)
            total_camera_trajectory_peak_turn_angle_delta_degrees += camera_trajectory_peak_turn_angle_delta
            if camera_trajectory_peak_turn_angle_delta != 0.0:
                camera_trajectory_peak_turn_angle_delta_pairs += 1

            camera_trajectory_turn_count_delta = int(scene_changes.get("camera_trajectory_turn_count_delta", 0) or 0)
            total_camera_trajectory_turn_count_delta += camera_trajectory_turn_count_delta
            if camera_trajectory_turn_count_delta != 0:
                camera_trajectory_turn_count_delta_pairs += 1

            camera_trajectory_average_turn_angle_delta = float(scene_changes.get("camera_trajectory_average_turn_angle_degrees_delta", 0.0) or 0.0)
            total_camera_trajectory_average_turn_angle_delta_degrees += camera_trajectory_average_turn_angle_delta
            if camera_trajectory_average_turn_angle_delta != 0.0:
                camera_trajectory_average_turn_angle_delta_pairs += 1

            camera_trajectory_turn_angle_standard_deviation_delta = float(
                scene_changes.get("camera_trajectory_turn_angle_standard_deviation_degrees_delta", 0.0) or 0.0
            )
            total_camera_trajectory_turn_angle_standard_deviation_delta_degrees += camera_trajectory_turn_angle_standard_deviation_delta
            if camera_trajectory_turn_angle_standard_deviation_delta != 0.0:
                camera_trajectory_turn_angle_standard_deviation_delta_pairs += 1

            camera_trajectory_point_delta = int(scene_changes.get("camera_trajectory_point_count_delta", 0) or 0)
            total_camera_trajectory_point_delta += camera_trajectory_point_delta
            if camera_trajectory_point_delta != 0:
                camera_trajectory_point_delta_pairs += 1

            if bool(scene_changes.get("camera_present_changed", False)):
                camera_present_changed_pairs += 1
            if bool(scene_changes.get("framing_intent_changed", False)):
                framing_intent_changed_pairs += 1
            if bool(scene_changes.get("camera_id_changed", False)):
                camera_id_changed_pairs += 1
            if bool(scene_changes.get("camera_has_trajectory_changed", False)):
                camera_has_trajectory_changed_pairs += 1
            if bool(scene_changes.get("camera_trajectory_changed", False)):
                camera_trajectory_changed_pairs += 1

            if bool(scene_changes.get("lighting_present_changed", False)):
                lighting_present_changed_pairs += 1

            light_count_delta = int(scene_changes.get("light_count_delta", 0) or 0)
            total_light_count_delta += light_count_delta
            if light_count_delta != 0:
                light_count_delta_pairs += 1

            light_intensity_total_delta = float(scene_changes.get("light_intensity_total_delta", 0.0) or 0.0)
            total_light_intensity_delta += light_intensity_total_delta
            if light_intensity_total_delta != 0.0:
                light_intensity_total_delta_pairs += 1

            if bool(scene_changes.get("light_intensity_range_changed", False)):
                light_intensity_range_changed_pairs += 1

            positioned_lights_delta = int(scene_changes.get("positioned_lights_delta", 0) or 0)
            total_positioned_lights_delta += positioned_lights_delta
            if positioned_lights_delta != 0:
                positioned_light_delta_pairs += 1

            directional_lights_delta = int(scene_changes.get("directional_lights_delta", 0) or 0)
            total_directional_lights_delta += directional_lights_delta
            if directional_lights_delta != 0:
                directional_light_delta_pairs += 1

            lights_with_temperature_delta = int(scene_changes.get("lights_with_temperature_delta", 0) or 0)
            total_lights_with_temperature_delta += lights_with_temperature_delta
            if lights_with_temperature_delta != 0:
                light_temperature_delta_pairs += 1

            if bool(scene_changes.get("light_temperature_range_changed", False)):
                light_temperature_range_changed_pairs += 1

            if bool(scene_changes.get("light_colors_changed", False)):
                light_colors_changed_pairs += 1
            if bool(scene_changes.get("light_ids_changed", False)):
                light_ids_changed_pairs += 1
            light_ids_count_delta = int(scene_changes.get("light_ids_count_delta", 0) or 0)
            total_light_ids_count_delta += light_ids_count_delta
            if light_ids_count_delta != 0:
                light_ids_count_delta_pairs += 1

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
            "object_ids_changed_pairs": object_ids_changed_pairs,
            "pairs_with_object_ids_count_delta": object_ids_count_delta_pairs,
            "total_object_ids_count_delta": total_object_ids_count_delta,
            "object_groups_changed_pairs": object_groups_changed_pairs,
            "pairs_with_object_groups_count_delta": object_groups_count_delta_pairs,
            "total_object_groups_count_delta": total_object_groups_count_delta,
            "appearance_classes_changed_pairs": appearance_classes_changed_pairs,
            "object_states_changed_pairs": object_states_changed_pairs,
            "object_visibilities_changed_pairs": object_visibilities_changed_pairs,
            "pairs_with_object_count_delta": object_count_delta_pairs,
            "total_object_count_delta": total_object_count_delta,
            "pairs_with_object_distance_delta": object_distance_delta_pairs,
            "total_object_distance_delta": total_object_distance_delta,
            "object_distance_range_changed_pairs": object_distance_range_changed_pairs,
            "pairs_with_positioned_object_delta": positioned_object_delta_pairs,
            "total_positioned_objects_delta": total_positioned_objects_delta,
            "pairs_with_orientation_delta": orientation_delta_pairs,
            "total_objects_with_orientation_delta": total_objects_with_orientation_delta,
            "pairs_with_trajectory_delta": trajectory_delta_pairs,
            "total_objects_with_trajectory_delta": total_objects_with_trajectory_delta,
            "pairs_with_trajectory_duration_delta": trajectory_duration_delta_pairs,
            "total_object_trajectory_duration_delta": total_object_trajectory_duration_delta,
            "trajectory_duration_range_changed_pairs": trajectory_duration_range_changed_pairs,
            "pairs_with_trajectory_path_length_delta": trajectory_path_length_delta_pairs,
            "total_object_trajectory_path_length_delta": total_object_trajectory_path_length_delta,
            "trajectory_path_length_range_changed_pairs": trajectory_path_length_range_changed_pairs,
            "pairs_with_trajectory_displacement_delta": trajectory_displacement_delta_pairs,
            "total_object_trajectory_displacement_delta": total_object_trajectory_displacement_delta,
            "trajectory_displacement_range_changed_pairs": trajectory_displacement_range_changed_pairs,
            "pairs_with_trajectory_average_speed_delta": trajectory_average_speed_delta_pairs,
            "total_object_trajectory_average_speed_delta": total_object_trajectory_average_speed_delta,
            "trajectory_average_speed_range_changed_pairs": trajectory_average_speed_range_changed_pairs,
            "pairs_with_trajectory_peak_speed_delta": trajectory_peak_speed_delta_pairs,
            "total_object_trajectory_peak_speed_delta": total_object_trajectory_peak_speed_delta,
            "trajectory_peak_speed_range_changed_pairs": trajectory_peak_speed_range_changed_pairs,
            "pairs_with_trajectory_speed_standard_deviation_delta": trajectory_speed_standard_deviation_delta_pairs,
            "total_object_trajectory_speed_standard_deviation_delta": total_object_trajectory_speed_standard_deviation_delta,
            "trajectory_speed_standard_deviation_range_changed_pairs": trajectory_speed_standard_deviation_range_changed_pairs,
            "pairs_with_trajectory_average_acceleration_delta": trajectory_average_acceleration_delta_pairs,
            "total_object_trajectory_average_acceleration_delta": total_object_trajectory_average_acceleration_delta,
            "trajectory_average_acceleration_range_changed_pairs": trajectory_average_acceleration_range_changed_pairs,
            "pairs_with_trajectory_peak_acceleration_delta": trajectory_peak_acceleration_delta_pairs,
            "total_object_trajectory_peak_acceleration_delta": total_object_trajectory_peak_acceleration_delta,
            "trajectory_peak_acceleration_range_changed_pairs": trajectory_peak_acceleration_range_changed_pairs,
            "pairs_with_trajectory_straightness_delta": trajectory_straightness_delta_pairs,
            "total_object_trajectory_straightness_delta": total_object_trajectory_straightness_delta,
            "trajectory_straightness_range_changed_pairs": trajectory_straightness_range_changed_pairs,
            "pairs_with_trajectory_turn_angle_delta": trajectory_turn_angle_delta_pairs,
            "total_object_trajectory_turn_angle_delta_degrees": total_object_trajectory_turn_angle_delta_degrees,
            "trajectory_turn_angle_range_changed_pairs": trajectory_turn_angle_range_changed_pairs,
            "pairs_with_trajectory_peak_turn_angle_delta": trajectory_peak_turn_angle_delta_pairs,
            "total_object_trajectory_peak_turn_angle_delta_degrees": total_object_trajectory_peak_turn_angle_delta_degrees,
            "trajectory_peak_turn_angle_range_changed_pairs": trajectory_peak_turn_angle_range_changed_pairs,
            "pairs_with_trajectory_turn_count_delta": trajectory_turn_count_delta_pairs,
            "total_object_trajectory_turn_count_delta": total_object_trajectory_turn_count_delta,
            "trajectory_turn_count_range_changed_pairs": trajectory_turn_count_range_changed_pairs,
            "pairs_with_trajectory_average_turn_angle_delta": trajectory_average_turn_angle_delta_pairs,
            "total_object_trajectory_average_turn_angle_delta_degrees": total_object_trajectory_average_turn_angle_delta_degrees,
            "trajectory_average_turn_angle_range_changed_pairs": trajectory_average_turn_angle_range_changed_pairs,
            "pairs_with_trajectory_turn_angle_standard_deviation_delta": trajectory_turn_angle_standard_deviation_delta_pairs,
            "total_object_trajectory_turn_angle_standard_deviation_delta_degrees": total_object_trajectory_turn_angle_standard_deviation_delta_degrees,
            "trajectory_turn_angle_standard_deviation_range_changed_pairs": trajectory_turn_angle_standard_deviation_range_changed_pairs,
            "pairs_with_trajectory_point_delta": trajectory_point_delta_pairs,
            "total_object_trajectory_point_delta": total_object_trajectory_point_delta,
            "camera_changed_pairs": camera_changed_pairs,
            "pairs_with_camera_distance_delta": camera_distance_delta_pairs,
            "total_camera_distance_delta": total_camera_distance_delta,
            "pairs_with_camera_trajectory_duration_delta": camera_trajectory_duration_delta_pairs,
            "total_camera_trajectory_duration_delta": total_camera_trajectory_duration_delta,
            "pairs_with_camera_trajectory_path_length_delta": camera_trajectory_path_length_delta_pairs,
            "total_camera_trajectory_path_length_delta": total_camera_trajectory_path_length_delta,
            "pairs_with_camera_trajectory_displacement_delta": camera_trajectory_displacement_delta_pairs,
            "total_camera_trajectory_displacement_delta": total_camera_trajectory_displacement_delta,
            "pairs_with_camera_trajectory_average_speed_delta": camera_trajectory_average_speed_delta_pairs,
            "total_camera_trajectory_average_speed_delta": total_camera_trajectory_average_speed_delta,
            "pairs_with_camera_trajectory_peak_speed_delta": camera_trajectory_peak_speed_delta_pairs,
            "total_camera_trajectory_peak_speed_delta": total_camera_trajectory_peak_speed_delta,
            "pairs_with_camera_trajectory_speed_standard_deviation_delta": camera_trajectory_speed_standard_deviation_delta_pairs,
            "total_camera_trajectory_speed_standard_deviation_delta": total_camera_trajectory_speed_standard_deviation_delta,
            "pairs_with_camera_trajectory_average_acceleration_delta": camera_trajectory_average_acceleration_delta_pairs,
            "total_camera_trajectory_average_acceleration_delta": total_camera_trajectory_average_acceleration_delta,
            "pairs_with_camera_trajectory_peak_acceleration_delta": camera_trajectory_peak_acceleration_delta_pairs,
            "total_camera_trajectory_peak_acceleration_delta": total_camera_trajectory_peak_acceleration_delta,
            "pairs_with_camera_trajectory_straightness_delta": camera_trajectory_straightness_delta_pairs,
            "total_camera_trajectory_straightness_delta": total_camera_trajectory_straightness_delta,
            "pairs_with_camera_trajectory_turn_angle_delta": camera_trajectory_turn_angle_delta_pairs,
            "total_camera_trajectory_turn_angle_delta_degrees": total_camera_trajectory_turn_angle_delta_degrees,
            "pairs_with_camera_trajectory_peak_turn_angle_delta": camera_trajectory_peak_turn_angle_delta_pairs,
            "total_camera_trajectory_peak_turn_angle_delta_degrees": total_camera_trajectory_peak_turn_angle_delta_degrees,
            "pairs_with_camera_trajectory_turn_count_delta": camera_trajectory_turn_count_delta_pairs,
            "total_camera_trajectory_turn_count_delta": total_camera_trajectory_turn_count_delta,
            "pairs_with_camera_trajectory_average_turn_angle_delta": camera_trajectory_average_turn_angle_delta_pairs,
            "total_camera_trajectory_average_turn_angle_delta_degrees": total_camera_trajectory_average_turn_angle_delta_degrees,
            "pairs_with_camera_trajectory_turn_angle_standard_deviation_delta": camera_trajectory_turn_angle_standard_deviation_delta_pairs,
            "total_camera_trajectory_turn_angle_standard_deviation_delta_degrees": total_camera_trajectory_turn_angle_standard_deviation_delta_degrees,
            "pairs_with_camera_trajectory_point_delta": camera_trajectory_point_delta_pairs,
            "total_camera_trajectory_point_delta": total_camera_trajectory_point_delta,
            "camera_present_changed_pairs": camera_present_changed_pairs,
            "framing_intent_changed_pairs": framing_intent_changed_pairs,
            "camera_id_changed_pairs": camera_id_changed_pairs,
            "camera_has_trajectory_changed_pairs": camera_has_trajectory_changed_pairs,
            "camera_trajectory_changed_pairs": camera_trajectory_changed_pairs,
            "lighting_present_changed_pairs": lighting_present_changed_pairs,
            "pairs_with_light_count_delta": light_count_delta_pairs,
            "total_light_count_delta": total_light_count_delta,
            "pairs_with_light_intensity_total_delta": light_intensity_total_delta_pairs,
            "total_light_intensity_delta": total_light_intensity_delta,
            "light_intensity_range_changed_pairs": light_intensity_range_changed_pairs,
            "pairs_with_positioned_light_delta": positioned_light_delta_pairs,
            "total_positioned_lights_delta": total_positioned_lights_delta,
            "pairs_with_directional_light_delta": directional_light_delta_pairs,
            "total_directional_lights_delta": total_directional_lights_delta,
            "pairs_with_light_temperature_delta": light_temperature_delta_pairs,
            "total_lights_with_temperature_delta": total_lights_with_temperature_delta,
            "light_temperature_range_changed_pairs": light_temperature_range_changed_pairs,
            "light_colors_changed_pairs": light_colors_changed_pairs,
            "light_ids_changed_pairs": light_ids_changed_pairs,
            "pairs_with_light_ids_count_delta": light_ids_count_delta_pairs,
            "total_light_ids_count_delta": total_light_ids_count_delta,
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
                "object_ids_changed",
                "object_count_delta",
                "object_groups_changed",
                "appearance_classes_changed",
                "object_states_changed",
                "object_visibilities_changed",
                "object_distance_from_origin_range_changed",
                "object_trajectory_duration_range_changed",
                "object_trajectory_path_length_range_changed",
                "object_trajectory_displacement_range_changed",
                "object_trajectory_average_speed_range_changed",
                "object_trajectory_peak_speed_range_changed",
                "object_trajectory_speed_standard_deviation_range_changed",
                "object_trajectory_average_acceleration_range_changed",
                "object_trajectory_peak_acceleration_range_changed",
                "object_trajectory_straightness_range_changed",
                "object_trajectory_turn_angle_range_degrees_changed",
                "object_trajectory_peak_turn_angle_range_degrees_changed",
                "object_trajectory_turn_count_range_changed",
                "object_trajectory_average_turn_angle_range_degrees_changed",
                "object_trajectory_turn_angle_standard_deviation_range_degrees_changed",
                "camera_changed",
                "camera_present_changed",
                "framing_intent_changed",
                "camera_id_changed",
                "camera_has_trajectory_changed",
                "camera_trajectory_changed",
                "lighting_present_changed",
                "light_intensity_range_changed",
                "light_temperature_range_changed",
                "light_colors_changed",
                "light_ids_changed",
            )
        ):
            return True
        if any(
            float(scene_changes.get(key, 0.0) or 0.0) != 0.0
            for key in (
                "object_distance_from_origin_total_delta",
                "object_trajectory_duration_total_delta",
                "object_trajectory_path_length_total_delta",
                "object_trajectory_displacement_total_delta",
                "object_trajectory_average_speed_total_delta",
                "object_trajectory_peak_speed_total_delta",
                "object_trajectory_speed_standard_deviation_total_delta",
                "object_trajectory_average_acceleration_total_delta",
                "object_trajectory_peak_acceleration_total_delta",
                "object_trajectory_straightness_total_delta",
                "object_trajectory_turn_angle_total_degrees_delta",
                "object_trajectory_peak_turn_angle_total_degrees_delta",
                "object_trajectory_average_turn_angle_total_degrees_delta",
                "object_trajectory_turn_angle_standard_deviation_total_degrees_delta",
                "camera_distance_from_origin_delta",
                "camera_trajectory_duration_delta",
                "camera_trajectory_path_length_delta",
                "camera_trajectory_displacement_delta",
                "camera_trajectory_average_speed_delta",
                "camera_trajectory_peak_speed_delta",
                "camera_trajectory_speed_standard_deviation_delta",
                "camera_trajectory_average_acceleration_delta",
                "camera_trajectory_peak_acceleration_delta",
                "camera_trajectory_straightness_delta",
                "camera_trajectory_turn_angle_degrees_delta",
                "camera_trajectory_peak_turn_angle_degrees_delta",
                "camera_trajectory_average_turn_angle_degrees_delta",
                "camera_trajectory_turn_angle_standard_deviation_degrees_delta",
                "light_intensity_total_delta",
            )
        ):
            return True
        if any(
            int(scene_changes.get(key, 0) or 0) != 0
            for key in (
                "positioned_objects_delta",
                "objects_with_orientation_delta",
                "objects_with_trajectory_delta",
                "object_count_delta",
                "object_trajectory_turn_count_total_delta",
                "camera_trajectory_turn_count_delta",
                "object_trajectory_point_count_delta",
                "camera_trajectory_point_count_delta",
                "light_count_delta",
                "positioned_lights_delta",
                "directional_lights_delta",
                "lights_with_temperature_delta",
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


def _rank_normalization_items(
    spec_counter: Counter[str],
    total_counter: Counter[str],
    spec_indexes: dict[str, list[int]],
    specs: dict[str, list[str]],
    normalized_count: int,
) -> list[dict[str, Any]]:
    denominator = normalized_count if normalized_count > 0 else 1
    ranked: list[dict[str, Any]] = []
    for name, spec_count in sorted(spec_counter.items(), key=lambda item: (-item[1], -total_counter[item[0]], item[0])):
        ranked.append(
            {
                "action": name,
                "specs_affected": spec_count,
                "total_count": total_counter[name],
                "spec_indexes": spec_indexes.get(name, []),
                "specs": specs.get(name, []),
                "frequency": spec_count / denominator,
            }
        )
    return ranked


def _rank_message_items(
    counter: Counter[str],
    spec_indexes: dict[str, list[int]],
    specs: dict[str, list[str]],
    label: str,
    total_count: int,
) -> list[dict[str, Any]]:
    denominator = total_count if total_count > 0 else 1
    ranked: list[dict[str, Any]] = []
    for message, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        ranked.append(
            {
                label: message,
                "specs_affected": count,
                "spec_indexes": spec_indexes.get(message, []),
                "specs": specs.get(message, []),
                "frequency": count / denominator,
            }
        )
    return ranked


def _estimate_assumption_count(
    result: dict[str, Any],
    normalization_summary: dict[str, Any] | None,
    source_warnings: list[str],
    normalized_warnings: list[str],
) -> int:
    explicit_count = result.get("assumption_count")
    if explicit_count is not None:
        return int(explicit_count or 0)

    derived_count = 0
    if normalization_summary is not None:
        derived_count += sum(1 for raw_count in normalization_summary.values() if int(raw_count or 0) > 0)
    derived_count += len(source_warnings)
    derived_count += len(normalized_warnings)
    return derived_count


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
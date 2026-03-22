from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import yaml

from ..writer.rwif_writer import load_wave_library
from .build import build_arwif_artifact
from .diff import diff_arwif_artifacts
from .export import export_arwif_artifact
from .importing import import_arwif_artifact
from .inspect import inspect_arwif_artifact
from .normalize import normalize_arwif_artifact
from .render import render_arwif_to_wav
from .validation import validate_arwif_artifact
from .validation import validate_arwif_spec


def batch_build_arwif_artifacts(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    built_count = 0
    failed_count = 0
    total_oscillator_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.arwif"
        try:
            payload = build_arwif_artifact(spec_path, output_path)
        except ValueError as exc:
            spec_report = validate_arwif_spec(spec_path)
            payload = {
                "artifact": str(output_path),
                "spec": str(spec_path),
                "built": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            }
            failed_count += 1
        else:
            built_count += 1
            total_oscillator_count += int(payload.get("oscillator_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "built_count": built_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch build output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_import_arwif_artifacts(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    imported_count = 0
    failed_count = 0
    total_oscillator_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.arwif"
        try:
            payload = import_arwif_artifact(spec_path, output_path)
        except ValueError as exc:
            spec_report = validate_arwif_spec(spec_path)
            payload = {
                "artifact": str(output_path),
                "spec": str(spec_path),
                "imported": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            }
            failed_count += 1
        else:
            imported_count += 1
            total_oscillator_count += int(payload.get("oscillator_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "imported_count": imported_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch import output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_validate_arwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for spec in specs:
        report = validate_arwif_spec(Path(spec))
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(report.stats.get("state_count", 0))
        total_oscillator_count += int(report.stats.get("oscillator_count", 0))
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate spec output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_validate_arwif_artifacts(
    artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(report.stats.get("state_count", 0))
        total_oscillator_count += _artifact_oscillator_count(artifact_path)
        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "allow_legacy": allow_legacy,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_inspect_arwif_artifacts(
    artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0
    max_frequency_hz = 0

    for artifact in artifacts:
        payload = inspect_arwif_artifact(Path(artifact), allow_legacy=allow_legacy)
        if payload.get("is_valid", False):
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(payload.get("state_count", 0))
        total_oscillator_count += int(payload.get("oscillator_count", 0))
        max_frequency_hz = max(max_frequency_hz, int(payload.get("max_frequency_hz") or 0))
        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "allow_legacy": allow_legacy,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "max_frequency_hz": max_frequency_hz,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch inspect output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def _artifact_oscillator_count(artifact_path: Path) -> int:
    try:
        library = load_wave_library(artifact_path)
    except Exception:
        return 0
    return sum(len(state.units) for state in library.states)


def batch_export_arwif_artifacts(
    artifacts: list[str | Path],
    output_dir: str | Path,
    *,
    format: str | None = None,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    if format is None:
        output_suffix = ".yaml"
        export_format = "yaml"
    elif format == "json":
        output_suffix = ".json"
        export_format = "json"
    elif format == "yaml":
        output_suffix = ".yaml"
        export_format = "yaml"
    else:
        raise ValueError("format must be yaml or json")

    results: list[dict[str, Any]] = []
    exported_count = 0
    failed_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        output_path = output_dir_path / f"{artifact_path.stem}.export{output_suffix}"
        try:
            payload = export_arwif_artifact(
                artifact_path,
                output_path,
                format=export_format,
                allow_legacy=allow_legacy,
            )
        except ValueError as exc:
            validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
            payload = {
                "artifact": str(artifact_path),
                "output": str(output_path),
                "format": export_format,
                "exported": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(validation_report.errors) or [str(exc)],
                "warnings": list(validation_report.warnings),
                "stats": dict(validation_report.stats),
            }
            failed_count += 1
        else:
            exported_count += 1
            total_state_count += int(payload.get("state_count", 0))
            total_oscillator_count += int(payload.get("oscillator_count", 0))
            payload["exported"] = True

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "exported_count": exported_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "format": export_format,
        "output_dir": str(output_dir_path),
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch export output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_normalize_arwif_artifacts(
    artifacts: list[str | Path],
    spec_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
    assumptions_dir: str | Path | None = None,
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    spec_dir_path = Path(spec_dir)
    output_dir_path = Path(output_dir) if output_dir is not None else None
    report_dir_path = Path(report_dir) if report_dir is not None else None
    assumptions_dir_path = Path(assumptions_dir) if assumptions_dir is not None else None

    if format is None:
        spec_suffix = ".yaml"
    elif format == "json":
        spec_suffix = ".json"
    elif format == "yaml":
        spec_suffix = ".yaml"
    else:
        raise ValueError("format must be yaml or json")

    spec_dir_path.mkdir(parents=True, exist_ok=True)
    if output_dir_path is not None:
        output_dir_path.mkdir(parents=True, exist_ok=True)
    if report_dir_path is not None:
        report_dir_path.mkdir(parents=True, exist_ok=True)
    if assumptions_dir_path is not None:
        assumptions_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    normalized_count = 0
    failed_count = 0
    total_assumption_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        stem = artifact_path.stem
        spec_output_path = spec_dir_path / f"{stem}.normalized{spec_suffix}"
        output_path = output_dir_path / f"{stem}.normalized.arwif" if output_dir_path is not None else None
        report_path = report_dir_path / f"{stem}.normalized.report.json" if report_dir_path is not None else None
        assumptions_path = (
            assumptions_dir_path / f"{stem}.normalized.assumptions.json"
            if assumptions_dir_path is not None
            else None
        )

        try:
            payload = normalize_arwif_artifact(
                artifact_path,
                spec_output_path,
                output=output_path,
                report=report_path,
                assumptions=assumptions_path,
                format=format,
            )
        except ValueError as exc:
            source_report = validate_arwif_artifact(artifact_path, allow_legacy=True)
            payload = {
                "artifact": str(artifact_path),
                "spec_output": str(spec_output_path),
                "output": str(output_path) if output_path is not None else None,
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
            total_assumption_count += int(payload.get("assumption_count", 0))

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "normalized_count": normalized_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("output_is_valid", True) for result in results),
        "format": format or "yaml",
        "spec_dir": str(spec_dir_path),
        "output_dir": str(output_dir_path) if output_dir_path is not None else None,
        "report_dir": str(report_dir_path) if report_dir_path is not None else None,
        "assumptions_dir": str(assumptions_dir_path) if assumptions_dir_path is not None else None,
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


def batch_render_arwif_artifacts(
    artifacts: list[str | Path],
    output_dir: str | Path,
    *,
    allow_legacy: bool = False,
    sample_rate_override: int | None = None,
    duration_override: float | None = None,
    normalize_override: bool | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    rendered_count = 0
    failed_count = 0
    total_duration_seconds = 0.0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        output_path = output_dir_path / f"{artifact_path.stem}.wav"
        try:
            payload = render_arwif_to_wav(
                artifact_path,
                output_path,
                allow_legacy=allow_legacy,
                sample_rate_override=sample_rate_override,
                duration_override=duration_override,
                normalize_override=normalize_override,
            )
        except ValueError as exc:
            validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
            payload = {
                "artifact": str(artifact_path),
                "output": str(output_path),
                "rendered": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(validation_report.errors) or [str(exc)],
                "warnings": list(validation_report.warnings),
                "stats": dict(validation_report.stats),
            }
            failed_count += 1
        else:
            rendered_count += 1
            total_duration_seconds += float(payload.get("duration_seconds", 0.0))
            payload["rendered"] = True

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "rendered_count": rendered_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("rendered", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_duration_seconds": total_duration_seconds,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch render output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_diff_arwif_artifacts(
    left_artifacts: list[str | Path],
    right_artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not left_artifacts or not right_artifacts:
        raise ValueError("at least one left and one right artifact must be provided")
    if len(left_artifacts) != len(right_artifacts):
        raise ValueError("left and right artifact collections must have the same length")

    results: list[dict[str, Any]] = []
    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    incompatible_pairs = 0
    total_metadata_fields_changed = 0
    total_changed_states = 0

    for pair_index, (left_artifact, right_artifact) in enumerate(zip(left_artifacts, right_artifacts, strict=True)):
        payload = diff_arwif_artifacts(left_artifact, right_artifact, allow_legacy=allow_legacy)
        payload["pair_index"] = pair_index

        summary = payload.get("change_summary", {})
        metadata_fields_changed = int(summary.get("metadata_fields_changed", 0))
        changed_states = int(summary.get("changed_states", 0))
        added_states = int(summary.get("added_states", 0))
        removed_states = int(summary.get("removed_states", 0))
        oscillator_count_delta = int(payload.get("oscillator_count_delta", 0))
        state_count_delta = int(payload.get("state_count_delta", 0))

        pair_changed = any(
            (
                metadata_fields_changed,
                changed_states,
                added_states,
                removed_states,
                oscillator_count_delta,
                state_count_delta,
            )
        )
        payload["pair_changed"] = pair_changed

        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not payload.get("left_valid", False) or not payload.get("right_valid", False):
            invalid_pairs += 1
        if not payload.get("compatible_format", False):
            incompatible_pairs += 1

        total_metadata_fields_changed += metadata_fields_changed
        total_changed_states += changed_states
        results.append(payload)

    payload = {
        "pairs_compared": len(results),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "incompatible_pairs": incompatible_pairs,
        "is_valid": invalid_pairs == 0,
        "allow_legacy": allow_legacy,
        "total_metadata_fields_changed": total_metadata_fields_changed,
        "total_changed_states": total_changed_states,
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


def batch_review_arwif_artifacts(
    left_artifacts: list[str | Path],
    right_artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    diff_payload = batch_diff_arwif_artifacts(
        left_artifacts,
        right_artifacts,
        allow_legacy=allow_legacy,
    )
    analysis_payload = _analyze_batch_diff_payload(diff_payload)

    review_payload = {
        "pairs_compared": diff_payload["pairs_compared"],
        "changed_pairs": diff_payload["changed_pairs"],
        "unchanged_pairs": diff_payload["unchanged_pairs"],
        "invalid_pairs": diff_payload["invalid_pairs"],
        "incompatible_pairs": diff_payload["incompatible_pairs"],
        "is_valid": diff_payload["is_valid"] and analysis_payload["is_valid"],
        "allow_legacy": allow_legacy,
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
    changed_state_counter: Counter[str] = Counter()
    added_state_counter: Counter[str] = Counter()
    removed_state_counter: Counter[str] = Counter()
    metadata_pair_indexes: dict[str, list[int]] = {}
    changed_state_pair_indexes: dict[str, list[int]] = {}
    added_state_pair_indexes: dict[str, list[int]] = {}
    removed_state_pair_indexes: dict[str, list[int]] = {}

    channel_layout_changed_pairs = 0
    listener_anchor_changed_pairs = 0
    reference_frame_changed_pairs = 0
    room_changed_pairs = 0
    room_dimensions_changed_pairs = 0
    geometry_reference_changed_pairs = 0
    room_geometry_id_changed_pairs = 0
    room_geometry_class_changed_pairs = 0
    room_surface_profile_changed_pairs = 0
    surface_treatment_changed_pairs = 0
    room_surface_absorption_changed_pairs = 0
    room_surface_diffusion_changed_pairs = 0
    reflection_policy_changed_pairs = 0
    room_reflection_style_changed_pairs = 0
    room_early_reflections_changed_pairs = 0
    room_late_reverb_changed_pairs = 0
    renderer_adaptation_changed_pairs = 0
    room_target_playback_changed_pairs = 0
    room_spatial_priority_changed_pairs = 0
    room_downmix_policy_changed_pairs = 0
    listening_zones_changed_pairs = 0
    listening_zone_delta_pairs = 0
    total_listening_zone_count_delta = 0
    speakers_changed_pairs = 0
    speaker_channels_changed_pairs = 0
    speaker_coverage_intents_changed_pairs = 0
    speaker_count_delta_pairs = 0
    total_speaker_count_delta = 0
    active_channels_changed_pairs = 0
    channel_gains_delta_pairs = 0
    total_states_with_channel_gains_delta = 0
    positioned_state_delta_pairs = 0
    total_positioned_states_delta = 0
    trajectory_changed_pairs = 0
    trajectory_state_delta_pairs = 0
    total_states_with_trajectory_delta = 0
    trajectory_point_delta_pairs = 0
    total_trajectory_point_delta = 0
    orientation_state_delta_pairs = 0
    total_states_with_orientation_delta = 0
    spread_state_delta_pairs = 0
    total_states_with_spread_delta = 0
    source_id_state_delta_pairs = 0
    total_states_with_source_id_delta = 0
    source_groups_changed_pairs = 0
    distance_models_changed_pairs = 0

    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    incompatible_pairs = 0

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
        if not raw_result.get("compatible_format", False):
            incompatible_pairs += 1

        metadata_changes = raw_result.get("metadata_changes")
        if isinstance(metadata_changes, dict):
            for field in metadata_changes:
                metadata_counter[str(field)] += 1
                metadata_pair_indexes.setdefault(str(field), []).append(pair_index)

        for state_name in _string_list(raw_result.get("changed_states")):
            changed_state_counter[state_name] += 1
            changed_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        for state_name in _string_list(raw_result.get("added_states")):
            added_state_counter[state_name] += 1
            added_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        for state_name in _string_list(raw_result.get("removed_states")):
            removed_state_counter[state_name] += 1
            removed_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        spatial_changes = raw_result.get("spatial_changes")
        if isinstance(spatial_changes, dict):
            if bool(spatial_changes.get("listener_anchor_changed", False)):
                listener_anchor_changed_pairs += 1
            if bool(spatial_changes.get("reference_frame_changed", False)):
                reference_frame_changed_pairs += 1
            if bool(spatial_changes.get("room_changed", False)):
                room_changed_pairs += 1
            if bool(spatial_changes.get("room_dimensions_changed", False)):
                room_dimensions_changed_pairs += 1
            if bool(spatial_changes.get("geometry_reference_changed", False)):
                geometry_reference_changed_pairs += 1
            if bool(spatial_changes.get("room_geometry_id_changed", False)):
                room_geometry_id_changed_pairs += 1
            if bool(spatial_changes.get("room_geometry_class_changed", False)):
                room_geometry_class_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_profile_changed", False)):
                room_surface_profile_changed_pairs += 1
            if bool(spatial_changes.get("surface_treatment_changed", False)):
                surface_treatment_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_absorption_changed", False)):
                room_surface_absorption_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_diffusion_changed", False)):
                room_surface_diffusion_changed_pairs += 1
            if bool(spatial_changes.get("reflection_policy_changed", False)):
                reflection_policy_changed_pairs += 1
            if bool(spatial_changes.get("room_reflection_style_changed", False)):
                room_reflection_style_changed_pairs += 1
            if bool(spatial_changes.get("room_early_reflections_changed", False)):
                room_early_reflections_changed_pairs += 1
            if bool(spatial_changes.get("room_late_reverb_changed", False)):
                room_late_reverb_changed_pairs += 1
            if bool(spatial_changes.get("renderer_adaptation_changed", False)):
                renderer_adaptation_changed_pairs += 1
            if bool(spatial_changes.get("room_target_playback_changed", False)):
                room_target_playback_changed_pairs += 1
            if bool(spatial_changes.get("room_spatial_priority_changed", False)):
                room_spatial_priority_changed_pairs += 1
            if bool(spatial_changes.get("room_downmix_policy_changed", False)):
                room_downmix_policy_changed_pairs += 1
            if bool(spatial_changes.get("listening_zones_changed", False)):
                listening_zones_changed_pairs += 1
            listening_zone_count_delta = int(spatial_changes.get("listening_zone_count_delta", 0) or 0)
            total_listening_zone_count_delta += listening_zone_count_delta
            if listening_zone_count_delta != 0:
                listening_zone_delta_pairs += 1
            if bool(spatial_changes.get("speakers_changed", False)):
                speakers_changed_pairs += 1
            if bool(spatial_changes.get("speaker_channels_changed", False)):
                speaker_channels_changed_pairs += 1
            if bool(spatial_changes.get("speaker_coverage_intents_changed", False)):
                speaker_coverage_intents_changed_pairs += 1
            speaker_count_delta = int(spatial_changes.get("speaker_count_delta", 0) or 0)
            total_speaker_count_delta += speaker_count_delta
            if speaker_count_delta != 0:
                speaker_count_delta_pairs += 1
            if bool(spatial_changes.get("channel_layout_changed", False)):
                channel_layout_changed_pairs += 1
            if bool(spatial_changes.get("active_channels_changed", False)):
                active_channels_changed_pairs += 1
            channel_gains_delta = int(spatial_changes.get("states_with_channel_gains_delta", 0) or 0)
            total_states_with_channel_gains_delta += channel_gains_delta
            if channel_gains_delta != 0:
                channel_gains_delta_pairs += 1
            positioned_states_delta = int(spatial_changes.get("positioned_states_delta", 0) or 0)
            total_positioned_states_delta += positioned_states_delta
            if positioned_states_delta != 0:
                positioned_state_delta_pairs += 1
            if bool(spatial_changes.get("trajectories_changed", False)):
                trajectory_changed_pairs += 1
            trajectory_states_delta = int(spatial_changes.get("states_with_trajectory_delta", 0) or 0)
            total_states_with_trajectory_delta += trajectory_states_delta
            if trajectory_states_delta != 0:
                trajectory_state_delta_pairs += 1
            trajectory_points_delta = int(spatial_changes.get("trajectory_point_count_delta", 0) or 0)
            total_trajectory_point_delta += trajectory_points_delta
            if trajectory_points_delta != 0:
                trajectory_point_delta_pairs += 1
            orientation_states_delta = int(spatial_changes.get("states_with_orientation_delta", 0) or 0)
            total_states_with_orientation_delta += orientation_states_delta
            if orientation_states_delta != 0:
                orientation_state_delta_pairs += 1
            spread_states_delta = int(spatial_changes.get("states_with_spread_delta", 0) or 0)
            total_states_with_spread_delta += spread_states_delta
            if spread_states_delta != 0:
                spread_state_delta_pairs += 1
            source_id_states_delta = int(spatial_changes.get("states_with_source_id_delta", 0) or 0)
            total_states_with_source_id_delta += source_id_states_delta
            if source_id_states_delta != 0:
                source_id_state_delta_pairs += 1
            if bool(spatial_changes.get("source_groups_changed", False)):
                source_groups_changed_pairs += 1
            if bool(spatial_changes.get("distance_models_changed", False)):
                distance_models_changed_pairs += 1

    pairs_compared = int(report_document.get("pairs_compared", len(results)))
    analysis_payload = {
        "pairs_compared": pairs_compared,
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "incompatible_pairs": incompatible_pairs,
        "is_valid": invalid_pairs == 0,
        "metadata_field_frequencies": _rank_frequency_items(metadata_counter, metadata_pair_indexes, "field", changed_pairs),
        "changed_state_frequencies": _rank_frequency_items(changed_state_counter, changed_state_pair_indexes, "state", changed_pairs),
        "added_state_frequencies": _rank_frequency_items(added_state_counter, added_state_pair_indexes, "state", changed_pairs),
        "removed_state_frequencies": _rank_frequency_items(removed_state_counter, removed_state_pair_indexes, "state", changed_pairs),
        "states_changed_in_all_changed_pairs": _universal_items(changed_state_counter, changed_pairs),
        "metadata_fields_changed_in_all_changed_pairs": _universal_items(metadata_counter, changed_pairs),
        "states_added_in_all_changed_pairs": _universal_items(added_state_counter, changed_pairs),
        "states_removed_in_all_changed_pairs": _universal_items(removed_state_counter, changed_pairs),
        "spatial_change_summary": {
            "listener_anchor_changed_pairs": listener_anchor_changed_pairs,
            "reference_frame_changed_pairs": reference_frame_changed_pairs,
            "room_changed_pairs": room_changed_pairs,
            "room_dimensions_changed_pairs": room_dimensions_changed_pairs,
            "geometry_reference_changed_pairs": geometry_reference_changed_pairs,
            "room_geometry_id_changed_pairs": room_geometry_id_changed_pairs,
            "room_geometry_class_changed_pairs": room_geometry_class_changed_pairs,
            "room_surface_profile_changed_pairs": room_surface_profile_changed_pairs,
            "surface_treatment_changed_pairs": surface_treatment_changed_pairs,
            "room_surface_absorption_changed_pairs": room_surface_absorption_changed_pairs,
            "room_surface_diffusion_changed_pairs": room_surface_diffusion_changed_pairs,
            "reflection_policy_changed_pairs": reflection_policy_changed_pairs,
            "room_reflection_style_changed_pairs": room_reflection_style_changed_pairs,
            "room_early_reflections_changed_pairs": room_early_reflections_changed_pairs,
            "room_late_reverb_changed_pairs": room_late_reverb_changed_pairs,
            "renderer_adaptation_changed_pairs": renderer_adaptation_changed_pairs,
            "room_target_playback_changed_pairs": room_target_playback_changed_pairs,
            "room_spatial_priority_changed_pairs": room_spatial_priority_changed_pairs,
            "room_downmix_policy_changed_pairs": room_downmix_policy_changed_pairs,
            "listening_zones_changed_pairs": listening_zones_changed_pairs,
            "pairs_with_listening_zone_count_delta": listening_zone_delta_pairs,
            "total_listening_zone_count_delta": total_listening_zone_count_delta,
            "speakers_changed_pairs": speakers_changed_pairs,
            "speaker_channels_changed_pairs": speaker_channels_changed_pairs,
            "speaker_coverage_intents_changed_pairs": speaker_coverage_intents_changed_pairs,
            "pairs_with_speaker_count_delta": speaker_count_delta_pairs,
            "total_speaker_count_delta": total_speaker_count_delta,
            "channel_layout_changed_pairs": channel_layout_changed_pairs,
            "active_channels_changed_pairs": active_channels_changed_pairs,
            "pairs_with_channel_gain_count_delta": channel_gains_delta_pairs,
            "total_states_with_channel_gains_delta": total_states_with_channel_gains_delta,
            "pairs_with_positioned_state_delta": positioned_state_delta_pairs,
            "total_positioned_states_delta": total_positioned_states_delta,
            "trajectory_changed_pairs": trajectory_changed_pairs,
            "pairs_with_trajectory_state_delta": trajectory_state_delta_pairs,
            "total_states_with_trajectory_delta": total_states_with_trajectory_delta,
            "pairs_with_trajectory_point_delta": trajectory_point_delta_pairs,
            "total_trajectory_point_delta": total_trajectory_point_delta,
            "pairs_with_orientation_state_delta": orientation_state_delta_pairs,
            "total_states_with_orientation_delta": total_states_with_orientation_delta,
            "pairs_with_spread_state_delta": spread_state_delta_pairs,
            "total_states_with_spread_delta": total_states_with_spread_delta,
            "pairs_with_source_id_state_delta": source_id_state_delta_pairs,
            "total_states_with_source_id_delta": total_states_with_source_id_delta,
            "source_groups_changed_pairs": source_groups_changed_pairs,
            "distance_models_changed_pairs": distance_models_changed_pairs,
        },
    }

    if analysis_input is not None:
        analysis_payload["analysis_input"] = analysis_input

    return analysis_payload


def _infer_pair_changed(result: dict[str, Any]) -> bool:
    summary = result.get("change_summary")
    if isinstance(summary, dict):
        if any(
            int(summary.get(key, 0) or 0)
            for key in ("metadata_fields_changed", "added_states", "removed_states", "changed_states")
        ):
            return True
    return any(
        int(result.get(key, 0) or 0)
        for key in ("state_count_delta", "oscillator_count_delta")
    )


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
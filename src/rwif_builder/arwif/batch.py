from __future__ import annotations

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

    return {
        "specs_processed": len(specs),
        "built_count": built_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }


def batch_import_arwif_artifacts(
    specs: list[str | Path],
    output_dir: str | Path,
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

    return {
        "specs_processed": len(specs),
        "imported_count": imported_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }


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

    return {
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


def batch_normalize_arwif_artifacts(
    artifacts: list[str | Path],
    spec_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
    assumptions_dir: str | Path | None = None,
    format: str | None = None,
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

    return {
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


def _resolve_auxiliary_format(output_path: Path, *, label: str) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError(f"could not infer {label} format from path; use a .json, .yaml, or .yml suffix")


def _write_auxiliary_document(output_path: Path, document: dict[str, Any], report_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
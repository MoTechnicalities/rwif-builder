from __future__ import annotations

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
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

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
        try:
            payload = normalize_vrwif_spec(spec_path, output_path, format=format)
        except ValueError as exc:
            source_report = validate_vrwif_spec(spec_path)
            payload = {
                "spec": str(spec_path),
                "output": str(output_path),
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
        added_objects = int(summary.get("added_objects", 0))
        removed_objects = int(summary.get("removed_objects", 0))

        pair_changed = any((metadata_fields_changed, changed_objects, added_objects, removed_objects))
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
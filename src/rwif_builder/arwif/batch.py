from __future__ import annotations

from pathlib import Path
from typing import Any

from .build import build_arwif_artifact
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

    return {
        "artifacts_processed": len(artifacts),
        "rendered_count": rendered_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("rendered", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_duration_seconds": total_duration_seconds,
        "results": results,
    }
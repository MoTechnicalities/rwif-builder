from __future__ import annotations

from pathlib import Path
from typing import Any

from .normalize import normalize_arwif_artifact
from .validation import validate_arwif_artifact


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
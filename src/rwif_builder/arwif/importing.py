from __future__ import annotations

from pathlib import Path
from typing import Any

from .build import build_arwif_artifact


def import_arwif_artifact(spec: str | Path, output: str | Path) -> dict[str, Any]:
    payload = build_arwif_artifact(spec, output)
    return {
        "artifact": payload["artifact"],
        "spec": payload["spec"],
        "state_count": payload["state_count"],
        "oscillator_count": payload["oscillator_count"],
        "spec_is_valid": payload["spec_is_valid"],
        "spec_validation_errors": payload["spec_validation_errors"],
        "spec_validation_warnings": payload["spec_validation_warnings"],
        "spec_validation_stats": payload["spec_validation_stats"],
        "is_valid": payload["is_valid"],
        "validation_errors": payload["validation_errors"],
        "validation_warnings": payload["validation_warnings"],
        "validation_stats": payload["validation_stats"],
        "imported": True,
    }
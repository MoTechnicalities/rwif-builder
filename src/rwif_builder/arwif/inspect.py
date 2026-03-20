from __future__ import annotations

from pathlib import Path
from typing import Any

from ..writer.rwif_writer import load_wave_library
from .validation import validate_arwif_artifact


def inspect_arwif_artifact(path: str | Path, *, allow_legacy: bool = False) -> dict[str, Any]:
    artifact_path = Path(path)
    library = load_wave_library(artifact_path)
    validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
    metadata = dict(library.metadata)

    state_summaries: list[dict[str, Any]] = []
    oscillator_count = 0
    max_frequency_hz = 0
    labels: list[str] = []

    for index, state in enumerate(library.states):
        state_metadata = dict(state.metadata or {})
        frequencies = [int(unit.frequency_index) for unit in state.units]
        amplitudes = [float(unit.amplitude) for unit in state.units]
        oscillator_count += len(frequencies)
        if frequencies:
            max_frequency_hz = max(max_frequency_hz, max(frequencies))
        if state.label:
            labels.append(str(state.label))
        state_summaries.append(
            {
                "index": index,
                "label": state.label,
                "oscillator_count": len(frequencies),
                "duration_seconds": state_metadata.get("duration_seconds", metadata.get("default_duration_seconds")),
                "attack_ms": state_metadata.get("attack_ms", metadata.get("default_attack_ms")),
                "release_ms": state_metadata.get("release_ms", metadata.get("default_release_ms")),
                "phase_radians": state_metadata.get("phase_radians", metadata.get("default_phase_radians", 0.0)),
                "gain": state_metadata.get("gain", 1.0),
                "min_frequency_hz": min(frequencies) if frequencies else None,
                "max_frequency_hz": max(frequencies) if frequencies else None,
                "max_amplitude": max((abs(amplitude) for amplitude in amplitudes), default=0.0),
                "sample_oscillators": [
                    {"hz": unit.frequency_index, "amplitude": unit.amplitude} for unit in state.units[:5]
                ],
            }
        )

    return {
        "artifact": str(artifact_path),
        "format": metadata.get("format"),
        "arwif_version": metadata.get("arwif_version"),
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "playback_model": metadata.get("playback_model"),
        "frequency_unit": metadata.get("frequency_unit"),
        "sample_rate_hz": metadata.get("sample_rate_hz"),
        "default_duration_seconds": metadata.get("default_duration_seconds"),
        "default_attack_ms": metadata.get("default_attack_ms"),
        "default_release_ms": metadata.get("default_release_ms"),
        "default_phase_radians": metadata.get("default_phase_radians"),
        "normalize": metadata.get("normalize"),
        "legacy_mode": validation_report.stats.get("legacy_mode", False),
        "is_valid": validation_report.is_valid,
        "errors": list(validation_report.errors),
        "warnings": list(validation_report.warnings),
        "state_count": len(library.states),
        "oscillator_count": oscillator_count,
        "max_frequency_hz": max_frequency_hz,
        "state_labels": labels,
        "states": state_summaries,
    }
from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

from ..writer.rwif_writer import WaveLibrary
from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import load_wave_library

ARWIF_FORMAT = "arwif_audio"
ARWIF_VERSION = 1
ARWIF_PLAYBACK_MODEL = "continuous_oscillator_bank"
ARWIF_FREQUENCY_UNIT = "hz"
DEFAULT_SAMPLE_RATE_HZ = 48_000
DEFAULT_DURATION_SECONDS = 1.0
DEFAULT_ATTACK_MS = 5.0
DEFAULT_RELEASE_MS = 5.0


@dataclass(frozen=True)
class ARWIFValidationReport:
    artifact: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _validate_required_metadata(
    metadata: dict[str, Any],
    *,
    allow_legacy: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    required = {
        "format": ARWIF_FORMAT,
        "arwif_version": ARWIF_VERSION,
        "frequency_unit": ARWIF_FREQUENCY_UNIT,
        "playback_model": ARWIF_PLAYBACK_MODEL,
    }
    for key, expected in required.items():
        actual = metadata.get(key)
        if actual == expected:
            continue
        message = f"library metadata {key!r} must be {expected!r}"
        if allow_legacy and actual is None:
            warnings.append(f"legacy mode: missing {key!r}; defaulting to {expected!r}")
            continue
        errors.append(message)


def _effective_sample_rate(metadata: dict[str, Any], allow_legacy: bool, errors: list[str], warnings: list[str]) -> int:
    sample_rate = metadata.get("sample_rate_hz")
    if isinstance(sample_rate, int) and sample_rate > 0:
        return sample_rate
    if allow_legacy and sample_rate is None:
        warnings.append(f"legacy mode: missing 'sample_rate_hz'; defaulting to {DEFAULT_SAMPLE_RATE_HZ}")
        return DEFAULT_SAMPLE_RATE_HZ
    errors.append("library metadata 'sample_rate_hz' must be a positive integer")
    return DEFAULT_SAMPLE_RATE_HZ


def _effective_default_duration(metadata: dict[str, Any], allow_legacy: bool, errors: list[str], warnings: list[str]) -> float:
    duration = metadata.get("default_duration_seconds")
    if _is_finite_number(duration) and float(duration) > 0.0:
        return float(duration)
    if allow_legacy and duration is None:
        warnings.append(
            f"legacy mode: missing 'default_duration_seconds'; defaulting to {DEFAULT_DURATION_SECONDS}"
        )
        return DEFAULT_DURATION_SECONDS
    errors.append("library metadata 'default_duration_seconds' must be a positive number")
    return DEFAULT_DURATION_SECONDS


def _effective_default_float(metadata: dict[str, Any], key: str, default: float) -> float:
    value = metadata.get(key)
    if _is_finite_number(value):
        return float(value)
    return default


def _state_metadata(state: WaveState) -> dict[str, Any]:
    return dict(state.metadata) if isinstance(state.metadata, dict) else {}


def _validate_state(
    state: WaveState,
    *,
    index: int,
    sample_rate_hz: int,
    default_duration_seconds: float,
    default_attack_ms: float,
    default_release_ms: float,
    errors: list[str],
    warnings: list[str],
) -> None:
    state_meta = _state_metadata(state)

    duration_seconds = state_meta.get("duration_seconds", default_duration_seconds)
    if not _is_finite_number(duration_seconds) or float(duration_seconds) <= 0.0:
        errors.append(f"state {index} duration_seconds must be a positive number")

    gain = state_meta.get("gain", 1.0)
    if not _is_finite_number(gain):
        errors.append(f"state {index} gain must be finite")

    phase_radians = state_meta.get("phase_radians", 0.0)
    if not _is_finite_number(phase_radians):
        errors.append(f"state {index} phase_radians must be finite")

    attack_ms = state_meta.get("attack_ms", default_attack_ms)
    if not _is_finite_number(attack_ms) or float(attack_ms) < 0.0:
        errors.append(f"state {index} attack_ms must be non-negative")

    release_ms = state_meta.get("release_ms", default_release_ms)
    if not _is_finite_number(release_ms) or float(release_ms) < 0.0:
        errors.append(f"state {index} release_ms must be non-negative")

    if not state.units:
        errors.append(f"state {index} has no wave units")

    if state.top_k <= 0:
        warnings.append(f"state {index} top_k is non-positive; ignored by ARWIF semantics")

    if state.vector_length <= 0:
        warnings.append(f"state {index} vector_length is non-positive; compatibility field is effectively unused")

    nyquist = sample_rate_hz / 2.0
    for unit in state.units:
        frequency_hz = unit.frequency_index
        amplitude = unit.amplitude
        if frequency_hz <= 0:
            errors.append(f"state {index} frequency must be positive, got {frequency_hz}")
        if frequency_hz >= nyquist:
            errors.append(f"state {index} frequency {frequency_hz} exceeds Nyquist {nyquist:.1f}")
        if not math.isfinite(amplitude):
            errors.append(f"state {index} amplitude for {frequency_hz} Hz must be finite")
        elif abs(amplitude) > 1.0:
            warnings.append(f"state {index} amplitude for {frequency_hz} Hz exceeds 1.0 and may need normalization")

    max_frequency = max((unit.frequency_index for unit in state.units), default=0)
    if state.vector_length > 0 and max_frequency >= state.vector_length:
        warnings.append(
            f"state {index} max frequency {max_frequency} exceeds vector_length {state.vector_length}; ARWIF ignores vector_length for Hz validation"
        )


def validate_arwif_artifact(path: str | Path, *, allow_legacy: bool = False) -> ARWIFValidationReport:
    artifact_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    try:
        library = load_wave_library(artifact_path)
    except Exception as exc:
        return ARWIFValidationReport(artifact=str(artifact_path), is_valid=False, errors=(str(exc),))

    metadata = dict(library.metadata)
    _validate_required_metadata(metadata, allow_legacy=allow_legacy, errors=errors, warnings=warnings)
    sample_rate_hz = _effective_sample_rate(metadata, allow_legacy, errors, warnings)
    default_duration_seconds = _effective_default_duration(metadata, allow_legacy, errors, warnings)
    default_attack_ms = _effective_default_float(metadata, "default_attack_ms", DEFAULT_ATTACK_MS)
    default_release_ms = _effective_default_float(metadata, "default_release_ms", DEFAULT_RELEASE_MS)

    stats["state_count"] = len(library.states)
    stats["sample_rate_hz"] = sample_rate_hz
    stats["default_duration_seconds"] = default_duration_seconds
    stats["legacy_mode"] = allow_legacy and metadata.get("format") != ARWIF_FORMAT

    if len(library.states) == 0:
        errors.append("ARWIF artifact must contain at least one state")

    total_duration_seconds = 0.0
    max_frequency_hz = 0
    for index, state in enumerate(library.states):
        _validate_state(
            state,
            index=index,
            sample_rate_hz=sample_rate_hz,
            default_duration_seconds=default_duration_seconds,
            default_attack_ms=default_attack_ms,
            default_release_ms=default_release_ms,
            errors=errors,
            warnings=warnings,
        )
        state_meta = _state_metadata(state)
        total_duration_seconds += float(state_meta.get("duration_seconds", default_duration_seconds))
        max_frequency_hz = max(max_frequency_hz, max((unit.frequency_index for unit in state.units), default=0))

    stats["total_duration_seconds"] = total_duration_seconds
    stats["max_frequency_hz"] = max_frequency_hz

    return ARWIFValidationReport(
        artifact=str(artifact_path),
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
    )
from __future__ import annotations

from pathlib import Path
import wave
from typing import Any

import numpy as np

from ..writer.rwif_writer import WaveState
from ..writer.rwif_writer import load_wave_library
from .validation import DEFAULT_ATTACK_MS
from .validation import DEFAULT_DURATION_SECONDS
from .validation import DEFAULT_RELEASE_MS
from .validation import DEFAULT_SAMPLE_RATE_HZ


def _state_metadata(state: WaveState) -> dict[str, Any]:
    return dict(state.metadata) if isinstance(state.metadata, dict) else {}


def _apply_envelope(samples: np.ndarray, sample_rate_hz: int, attack_ms: float, release_ms: float) -> np.ndarray:
    if samples.size == 0:
        return samples
    envelope = np.ones_like(samples)
    attack_count = min(samples.size, int(sample_rate_hz * attack_ms / 1000.0))
    release_count = min(samples.size, int(sample_rate_hz * release_ms / 1000.0))
    if attack_count > 1:
        envelope[:attack_count] = np.linspace(0.0, 1.0, attack_count, endpoint=True)
    if release_count > 1:
        envelope[-release_count:] *= np.linspace(1.0, 0.0, release_count, endpoint=True)
    return samples * envelope


def _render_state(
    state: WaveState,
    *,
    sample_rate_hz: int,
    default_duration_seconds: float,
    default_attack_ms: float,
    default_release_ms: float,
    phase_radians: float,
) -> np.ndarray:
    state_meta = _state_metadata(state)
    duration_seconds = float(state_meta.get("duration_seconds", default_duration_seconds))
    gain = float(state_meta.get("gain", 1.0))
    phase = float(state_meta.get("phase_radians", phase_radians))
    attack_ms = float(state_meta.get("attack_ms", default_attack_ms))
    release_ms = float(state_meta.get("release_ms", default_release_ms))
    sample_count = max(1, int(round(duration_seconds * sample_rate_hz)))
    time_axis = np.arange(sample_count, dtype=np.float64) / float(sample_rate_hz)
    samples = np.zeros(sample_count, dtype=np.float64)
    for unit in state.units:
        samples += float(unit.amplitude) * np.sin((2.0 * np.pi * float(unit.frequency_index) * time_axis) + phase)
    samples *= gain
    return _apply_envelope(samples, sample_rate_hz, attack_ms, release_ms)


def render_arwif_to_wav(
    artifact: str | Path,
    output: str | Path,
    *,
    allow_legacy: bool = False,
    sample_rate_override: int | None = None,
    duration_override: float | None = None,
    normalize_override: bool | None = None,
) -> dict[str, Any]:
    artifact_path = Path(artifact)
    output_path = Path(output)
    library = load_wave_library(artifact_path)
    metadata = dict(library.metadata)

    sample_rate_hz = sample_rate_override or int(metadata.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ))
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")

    default_duration_seconds = duration_override if duration_override is not None else float(
        metadata.get("default_duration_seconds", DEFAULT_DURATION_SECONDS)
    )
    if default_duration_seconds <= 0.0:
        raise ValueError("default_duration_seconds must be positive")

    normalize = normalize_override
    if normalize is None:
        normalize = bool(metadata.get("normalize", True))
    default_phase_radians = float(metadata.get("default_phase_radians", 0.0))
    default_attack_ms = float(metadata.get("default_attack_ms", DEFAULT_ATTACK_MS))
    default_release_ms = float(metadata.get("default_release_ms", DEFAULT_RELEASE_MS))

    rendered_segments: list[np.ndarray] = []
    for state in library.states:
        rendered_segments.append(
            _render_state(
                state,
                sample_rate_hz=sample_rate_hz,
                default_duration_seconds=default_duration_seconds,
                default_attack_ms=default_attack_ms,
                default_release_ms=default_release_ms,
                phase_radians=default_phase_radians,
            )
        )

    if not rendered_segments:
        raise ValueError("ARWIF artifact contains no states to render")

    mixed = np.concatenate(rendered_segments)
    peak_before = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    normalized = False
    if normalize and peak_before > 0.0:
        scale = max(1.0, peak_before)
        mixed = mixed / scale
        normalized = scale > 1.0

    peak_after = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    pcm = np.clip(mixed, -1.0, 1.0)
    pcm16 = np.round(pcm * 32767.0).astype(np.int16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(pcm16.tobytes())

    return {
        "artifact": str(artifact_path),
        "output": str(output_path),
        "sample_rate_hz": sample_rate_hz,
        "segment_count": len(rendered_segments),
        "duration_seconds": len(pcm16) / float(sample_rate_hz),
        "legacy_mode": allow_legacy and metadata.get("format") != "arwif_audio",
        "normalized": normalized,
        "peak_before": peak_before,
        "peak_after": peak_after,
    }
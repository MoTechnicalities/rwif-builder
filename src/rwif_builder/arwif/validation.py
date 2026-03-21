from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

import yaml

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
SPATIAL_VECTOR_AXES = ("x", "y", "z")
OBJECT_DISTANCE_MODELS = ("none", "inverse", "linear", "exponential")

CHANNEL_LAYOUT_CHANNELS: dict[str, tuple[str, ...]] = {
    "mono": ("C",),
    "stereo": ("L", "R"),
    "quad": ("FL", "FR", "RL", "RR"),
    "5.1": ("FL", "FR", "C", "LFE", "SL", "SR"),
    "7.1": ("FL", "FR", "C", "LFE", "SL", "SR", "RL", "RR"),
}

_LIBRARY_OVERRIDE_KEYS = {
    "format",
    "arwif_version",
    "frequency_unit",
    "playback_model",
    "sample_rate_hz",
    "default_duration_seconds",
    "normalize",
    "default_phase_radians",
    "default_attack_ms",
    "default_release_ms",
    "channel_layout",
    "listener_anchor",
}


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


@dataclass(frozen=True)
class ARWIFSpecValidationReport:
    spec: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)
    normalized_document: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "spec": self.spec,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }
        if self.normalized_document is not None:
            payload["normalized_document"] = dict(self.normalized_document)
        return payload


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _is_non_negative_number(value: Any) -> bool:
    return _is_number(value) and float(value) >= 0.0


def _is_positive_number(value: Any) -> bool:
    return _is_number(value) and float(value) > 0.0


def _deep_copy_document(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy_document(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy_document(item) for item in value]
    return value


def _load_spec_document(spec_path: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    try:
        with spec_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except Exception as exc:
        return None, (str(exc),)

    if document is None:
        return None, ("ARWIF spec file is empty",)
    if not isinstance(document, dict):
        return None, ("ARWIF spec must be a mapping",)
    return document, ()


def _validate_spatial_vector_mapping(
    value: Any,
    *,
    context: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{context} must be a mapping")
        return

    unknown_keys = sorted(key for key in value if key not in SPATIAL_VECTOR_AXES)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    for axis in SPATIAL_VECTOR_AXES:
        if not _is_number(value.get(axis)):
            errors.append(f"{context}.{axis} must be a finite number")


def _validate_trajectory_mapping(
    value: Any,
    *,
    context: str,
    max_offset_seconds: float | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{context} must be a list")
        return
    if not value:
        errors.append(f"{context} must contain at least one keyframe")
        return

    previous_offset: float | None = None
    for index, keyframe in enumerate(value):
        keyframe_context = f"{context}[{index}]"
        if not isinstance(keyframe, dict):
            errors.append(f"{keyframe_context} must be a mapping")
            continue

        unknown_keys = sorted(key for key in keyframe if key not in {"offset_seconds", "position"})
        if unknown_keys:
            warnings.append(
                f"{keyframe_context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}"
            )

        offset_seconds = keyframe.get("offset_seconds")
        if not _is_non_negative_number(offset_seconds):
            errors.append(f"{keyframe_context}.offset_seconds must be a non-negative finite number")
        else:
            offset_value = float(offset_seconds)
            if max_offset_seconds is not None and offset_value > max_offset_seconds:
                errors.append(
                    f"{keyframe_context}.offset_seconds must not exceed state duration {max_offset_seconds}"
                )
            if previous_offset is not None and offset_value < previous_offset:
                errors.append(f"{context} must be sorted by non-decreasing offset_seconds")
            previous_offset = offset_value

        _validate_spatial_vector_mapping(
            keyframe.get("position"),
            context=f"{keyframe_context}.position",
            errors=errors,
            warnings=warnings,
        )


def _validate_top_level(document: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    allowed_keys = {
        "title",
        "description",
        "channel_layout",
        "listener_anchor",
        "sample_rate_hz",
        "default_duration_seconds",
        "default_phase_radians",
        "default_attack_ms",
        "default_release_ms",
        "normalize",
        "metadata",
        "states",
    }
    unknown_keys = sorted(key for key in document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"unknown top-level fields ignored by the reference builder: {', '.join(unknown_keys)}")

    if "title" in document and not isinstance(document["title"], str):
        errors.append("title must be a string")
    if "description" in document and not isinstance(document["description"], str):
        errors.append("description must be a string")

    channel_layout = document.get("channel_layout")
    if channel_layout is not None:
        if not isinstance(channel_layout, str):
            errors.append("channel_layout must be a string")
        elif channel_layout not in CHANNEL_LAYOUT_CHANNELS:
            errors.append("channel_layout must be one of: " + ", ".join(sorted(CHANNEL_LAYOUT_CHANNELS)))

    if "listener_anchor" in document:
        _validate_spatial_vector_mapping(
            document.get("listener_anchor"),
            context="listener_anchor",
            errors=errors,
            warnings=warnings,
        )

    sample_rate_hz = document.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ)
    if not _is_positive_int(sample_rate_hz):
        errors.append("sample_rate_hz must be a positive integer")

    default_duration_seconds = document.get("default_duration_seconds", DEFAULT_DURATION_SECONDS)
    if not _is_positive_number(default_duration_seconds):
        errors.append("default_duration_seconds must be a positive number")

    default_phase_radians = document.get("default_phase_radians", 0.0)
    if not _is_number(default_phase_radians):
        errors.append("default_phase_radians must be a finite number")

    default_attack_ms = document.get("default_attack_ms", DEFAULT_ATTACK_MS)
    if not _is_non_negative_number(default_attack_ms):
        errors.append("default_attack_ms must be non-negative")

    default_release_ms = document.get("default_release_ms", DEFAULT_RELEASE_MS)
    if not _is_non_negative_number(default_release_ms):
        errors.append("default_release_ms must be non-negative")

    normalize = document.get("normalize", True)
    if not _is_bool(normalize):
        errors.append("normalize must be a boolean")

    metadata = document.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            errors.append("metadata must be a mapping")
        else:
            reserved_keys = sorted(key for key in metadata if key in _LIBRARY_OVERRIDE_KEYS)
            if reserved_keys:
                warnings.append(
                    "metadata contains reserved library fields that will be overridden: "
                    + ", ".join(reserved_keys)
                )

    states = document.get("states")
    if not isinstance(states, list):
        errors.append("states must be a list")
        return
    if not states:
        errors.append("states must contain at least one state")


def _validate_state_document(
    state_document: Any,
    *,
    index: int,
    sample_rate_hz: int,
    channel_layout: str | None,
    errors: list[str],
    warnings: list[str],
) -> int:
    context = f"states[{index}]"
    if not isinstance(state_document, dict):
        errors.append(f"{context} must be a mapping")
        return 0

    allowed_keys = {
        "label",
        "duration_seconds",
        "phase_radians",
        "gain",
        "channel_gains",
        "position",
        "trajectory",
        "orientation",
        "spread",
        "distance_model",
        "attack_ms",
        "release_ms",
        "vector_length",
        "top_k",
        "metadata",
        "oscillators",
        "centered_norm",
        "original_norm",
    }
    unknown_keys = sorted(key for key in state_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    if "label" in state_document and state_document["label"] is not None and not isinstance(state_document["label"], str):
        errors.append(f"{context}.label must be a string")

    if "duration_seconds" in state_document and not _is_positive_number(state_document["duration_seconds"]):
        errors.append(f"{context}.duration_seconds must be a positive number")
    if "phase_radians" in state_document and not _is_number(state_document["phase_radians"]):
        errors.append(f"{context}.phase_radians must be a finite number")
    if "gain" in state_document and not _is_number(state_document["gain"]):
        errors.append(f"{context}.gain must be a finite number")
    if "channel_gains" in state_document:
        channel_gains = state_document["channel_gains"]
        if not isinstance(channel_gains, dict):
            errors.append(f"{context}.channel_gains must be a mapping")
        elif channel_layout is None:
            errors.append(f"{context}.channel_gains requires top-level channel_layout")
        else:
            allowed_channels = set(CHANNEL_LAYOUT_CHANNELS[channel_layout])
            for channel_name, gain_value in channel_gains.items():
                if not isinstance(channel_name, str) or not channel_name:
                    errors.append(f"{context}.channel_gains keys must be non-empty strings")
                    continue
                if channel_name not in allowed_channels:
                    errors.append(
                        f"{context}.channel_gains contains unknown channel {channel_name!r} for layout {channel_layout!r}"
                    )
                if not _is_number(gain_value):
                    errors.append(f"{context}.channel_gains[{channel_name!r}] must be a finite number")
    if "position" in state_document:
        _validate_spatial_vector_mapping(
            state_document.get("position"),
            context=f"{context}.position",
            errors=errors,
            warnings=warnings,
        )
    duration_seconds = state_document.get("duration_seconds", DEFAULT_DURATION_SECONDS)
    max_offset_seconds = float(duration_seconds) if _is_positive_number(duration_seconds) else None
    if "trajectory" in state_document:
        _validate_trajectory_mapping(
            state_document.get("trajectory"),
            context=f"{context}.trajectory",
            max_offset_seconds=max_offset_seconds,
            errors=errors,
            warnings=warnings,
        )
    if "orientation" in state_document:
        _validate_spatial_vector_mapping(
            state_document.get("orientation"),
            context=f"{context}.orientation",
            errors=errors,
            warnings=warnings,
        )
    if "spread" in state_document and not _is_non_negative_number(state_document["spread"]):
        errors.append(f"{context}.spread must be non-negative")
    if "distance_model" in state_document:
        distance_model = state_document["distance_model"]
        if not isinstance(distance_model, str):
            errors.append(f"{context}.distance_model must be a string")
        elif distance_model not in OBJECT_DISTANCE_MODELS:
            errors.append(
                f"{context}.distance_model must be one of: " + ", ".join(OBJECT_DISTANCE_MODELS)
            )
    if "attack_ms" in state_document and not _is_non_negative_number(state_document["attack_ms"]):
        errors.append(f"{context}.attack_ms must be non-negative")
    if "release_ms" in state_document and not _is_non_negative_number(state_document["release_ms"]):
        errors.append(f"{context}.release_ms must be non-negative")
    if "vector_length" in state_document and not _is_positive_int(state_document["vector_length"]):
        errors.append(f"{context}.vector_length must be a positive integer")
    if "top_k" in state_document and not _is_positive_int(state_document["top_k"]):
        errors.append(f"{context}.top_k must be a positive integer")
    if "centered_norm" in state_document and not _is_number(state_document["centered_norm"]):
        errors.append(f"{context}.centered_norm must be a finite number")
    if "original_norm" in state_document and not _is_number(state_document["original_norm"]):
        errors.append(f"{context}.original_norm must be a finite number")

    state_metadata = state_document.get("metadata")
    if state_metadata is not None and not isinstance(state_metadata, dict):
        errors.append(f"{context}.metadata must be a mapping")

    oscillators = state_document.get("oscillators")
    if not isinstance(oscillators, list):
        errors.append(f"{context}.oscillators must be a list")
        return 0
    if not oscillators:
        errors.append(f"{context}.oscillators must contain at least one oscillator")
        return 0

    nyquist = sample_rate_hz / 2.0
    oscillator_count = 0
    for oscillator_index, oscillator in enumerate(oscillators):
        oscillator_context = f"{context}.oscillators[{oscillator_index}]"
        if not isinstance(oscillator, dict):
            errors.append(f"{oscillator_context} must be a mapping")
            continue

        unknown_oscillator_keys = sorted(key for key in oscillator if key not in {"hz", "amplitude"})
        if unknown_oscillator_keys:
            warnings.append(
                f"{oscillator_context} contains unknown fields ignored by the reference builder: {', '.join(unknown_oscillator_keys)}"
            )

        hz = oscillator.get("hz")
        amplitude = oscillator.get("amplitude")
        if not _is_positive_int(hz):
            errors.append(f"{oscillator_context}.hz must be a positive integer")
        elif hz >= nyquist:
            errors.append(f"{oscillator_context}.hz {hz} exceeds Nyquist {nyquist:.1f}")

        if not _is_number(amplitude):
            errors.append(f"{oscillator_context}.amplitude must be a finite number")
        elif abs(float(amplitude)) > 1.0:
            warnings.append(f"{oscillator_context}.amplitude exceeds 1.0 and may require normalization")

        oscillator_count += 1

    return oscillator_count


def validate_arwif_spec(path: str | Path) -> ARWIFSpecValidationReport:
    spec_path = Path(path)
    document, load_errors = _load_spec_document(spec_path)
    if load_errors:
        return ARWIFSpecValidationReport(spec=str(spec_path), is_valid=False, errors=load_errors)

    assert document is not None
    return validate_arwif_spec_document(document, source=str(spec_path))


def validate_arwif_spec_document(document: dict[str, Any], *, source: str = "<memory>") -> ARWIFSpecValidationReport:
    if not isinstance(document, dict):
        return ARWIFSpecValidationReport(spec=source, is_valid=False, errors=("ARWIF spec must be a mapping",))

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    _validate_top_level(document, errors, warnings)
    sample_rate_hz = document.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ)
    channel_layout = document.get("channel_layout") if isinstance(document.get("channel_layout"), str) else None
    state_count = 0
    oscillator_count = 0
    positioned_state_count = 0
    states_with_trajectory = 0
    trajectory_point_count = 0
    states_with_orientation = 0
    states_with_spread = 0
    distance_models: set[str] = set()
    if isinstance(document.get("states"), list):
        states = document["states"]
        state_count = len(states)
        if _is_positive_int(sample_rate_hz):
            for index, state_document in enumerate(states):
                if isinstance(state_document, dict):
                    if isinstance(state_document.get("position"), dict):
                        positioned_state_count += 1
                    if isinstance(state_document.get("trajectory"), list) and state_document.get("trajectory"):
                        states_with_trajectory += 1
                        trajectory_point_count += len(state_document["trajectory"])
                    if isinstance(state_document.get("orientation"), dict):
                        states_with_orientation += 1
                    if _is_non_negative_number(state_document.get("spread")):
                        states_with_spread += 1
                    distance_model = state_document.get("distance_model")
                    if isinstance(distance_model, str) and distance_model in OBJECT_DISTANCE_MODELS:
                        distance_models.add(distance_model)
                oscillator_count += _validate_state_document(
                    state_document,
                    index=index,
                    sample_rate_hz=sample_rate_hz,
                    channel_layout=channel_layout,
                    errors=errors,
                    warnings=warnings,
                )

    stats["state_count"] = state_count
    stats["oscillator_count"] = oscillator_count
    if _is_positive_int(sample_rate_hz):
        stats["sample_rate_hz"] = int(sample_rate_hz)
    if channel_layout in CHANNEL_LAYOUT_CHANNELS:
        stats["channel_layout"] = channel_layout
        stats["channel_count"] = len(CHANNEL_LAYOUT_CHANNELS[channel_layout])
    stats["listener_anchor_present"] = isinstance(document.get("listener_anchor"), dict)
    stats["positioned_state_count"] = positioned_state_count
    stats["states_with_trajectory"] = states_with_trajectory
    stats["trajectory_point_count"] = trajectory_point_count
    stats["states_with_orientation"] = states_with_orientation
    stats["states_with_spread"] = states_with_spread
    stats["distance_models"] = sorted(distance_models)
    default_duration_seconds = document.get("default_duration_seconds", DEFAULT_DURATION_SECONDS)
    if _is_positive_number(default_duration_seconds):
        stats["default_duration_seconds"] = float(default_duration_seconds)

    normalized_document = _deep_copy_document(document) if not errors else None
    return ARWIFSpecValidationReport(
        spec=source,
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
        normalized_document=normalized_document,
    )


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
    channel_layout: str | None,
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

    channel_gains = state_meta.get("channel_gains")
    if channel_gains is not None:
        if not isinstance(channel_gains, dict):
            errors.append(f"state {index} channel_gains must be a mapping")
        elif channel_layout is None:
            errors.append(f"state {index} channel_gains requires library channel_layout")
        else:
            allowed_channels = set(CHANNEL_LAYOUT_CHANNELS[channel_layout])
            for channel_name, gain_value in channel_gains.items():
                if not isinstance(channel_name, str) or not channel_name:
                    errors.append(f"state {index} channel_gains keys must be non-empty strings")
                    continue
                if channel_name not in allowed_channels:
                    errors.append(
                        f"state {index} channel_gains contains unknown channel {channel_name!r} for layout {channel_layout!r}"
                    )
                if not _is_finite_number(gain_value):
                    errors.append(f"state {index} channel_gains[{channel_name!r}] must be finite")

    position = state_meta.get("position")
    if position is not None:
        _validate_spatial_vector_mapping(
            position,
            context=f"state {index} position",
            errors=errors,
            warnings=warnings,
        )

    if "trajectory" in state_meta:
        max_offset_seconds = float(duration_seconds) if _is_finite_number(duration_seconds) and float(duration_seconds) > 0.0 else None
        _validate_trajectory_mapping(
            state_meta.get("trajectory"),
            context=f"state {index} trajectory",
            max_offset_seconds=max_offset_seconds,
            errors=errors,
            warnings=warnings,
        )

    orientation = state_meta.get("orientation")
    if orientation is not None:
        _validate_spatial_vector_mapping(
            orientation,
            context=f"state {index} orientation",
            errors=errors,
            warnings=warnings,
        )

    spread = state_meta.get("spread")
    if spread is not None and (not _is_finite_number(spread) or float(spread) < 0.0):
        errors.append(f"state {index} spread must be non-negative")

    distance_model = state_meta.get("distance_model")
    if distance_model is not None:
        if not isinstance(distance_model, str):
            errors.append(f"state {index} distance_model must be a string")
        elif distance_model not in OBJECT_DISTANCE_MODELS:
            errors.append(
                f"state {index} distance_model must be one of: " + ", ".join(OBJECT_DISTANCE_MODELS)
            )

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
    channel_layout = metadata.get("channel_layout")
    if channel_layout is not None:
        if not isinstance(channel_layout, str) or channel_layout not in CHANNEL_LAYOUT_CHANNELS:
            errors.append("library metadata 'channel_layout' must be one of: " + ", ".join(sorted(CHANNEL_LAYOUT_CHANNELS)))
            channel_layout = None
    listener_anchor = metadata.get("listener_anchor")
    if listener_anchor is not None:
        _validate_spatial_vector_mapping(
            listener_anchor,
            context="library metadata 'listener_anchor'",
            errors=errors,
            warnings=warnings,
        )
    default_duration_seconds = _effective_default_duration(metadata, allow_legacy, errors, warnings)
    default_attack_ms = _effective_default_float(metadata, "default_attack_ms", DEFAULT_ATTACK_MS)
    default_release_ms = _effective_default_float(metadata, "default_release_ms", DEFAULT_RELEASE_MS)

    stats["state_count"] = len(library.states)
    stats["sample_rate_hz"] = sample_rate_hz
    stats["default_duration_seconds"] = default_duration_seconds
    stats["legacy_mode"] = allow_legacy and metadata.get("format") != ARWIF_FORMAT
    if channel_layout is not None:
        stats["channel_layout"] = channel_layout
        stats["channel_count"] = len(CHANNEL_LAYOUT_CHANNELS[channel_layout])
    stats["listener_anchor_present"] = isinstance(listener_anchor, dict)

    if len(library.states) == 0:
        errors.append("ARWIF artifact must contain at least one state")

    total_duration_seconds = 0.0
    max_frequency_hz = 0
    positioned_state_count = 0
    states_with_trajectory = 0
    trajectory_point_count = 0
    states_with_orientation = 0
    states_with_spread = 0
    distance_models: set[str] = set()
    for index, state in enumerate(library.states):
        _validate_state(
            state,
            index=index,
            sample_rate_hz=sample_rate_hz,
            channel_layout=channel_layout,
            default_duration_seconds=default_duration_seconds,
            default_attack_ms=default_attack_ms,
            default_release_ms=default_release_ms,
            errors=errors,
            warnings=warnings,
        )
        state_meta = _state_metadata(state)
        if isinstance(state_meta.get("position"), dict):
            positioned_state_count += 1
        if isinstance(state_meta.get("trajectory"), list) and state_meta.get("trajectory"):
            states_with_trajectory += 1
            trajectory_point_count += len(state_meta["trajectory"])
        if isinstance(state_meta.get("orientation"), dict):
            states_with_orientation += 1
        if _is_finite_number(state_meta.get("spread")) and float(state_meta.get("spread")) >= 0.0:
            states_with_spread += 1
        distance_model = state_meta.get("distance_model")
        if isinstance(distance_model, str) and distance_model in OBJECT_DISTANCE_MODELS:
            distance_models.add(distance_model)
        total_duration_seconds += float(state_meta.get("duration_seconds", default_duration_seconds))
        max_frequency_hz = max(max_frequency_hz, max((unit.frequency_index for unit in state.units), default=0))

    stats["total_duration_seconds"] = total_duration_seconds
    stats["max_frequency_hz"] = max_frequency_hz
    stats["positioned_state_count"] = positioned_state_count
    stats["states_with_trajectory"] = states_with_trajectory
    stats["trajectory_point_count"] = trajectory_point_count
    stats["states_with_orientation"] = states_with_orientation
    stats["states_with_spread"] = states_with_spread
    stats["distance_models"] = sorted(distance_models)

    return ARWIFValidationReport(
        artifact=str(artifact_path),
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
    )
from __future__ import annotations

from dataclasses import dataclass
import tempfile
import subprocess
import wave
from pathlib import Path
from shutil import which

from demucs.apply import apply_model
from demucs.pretrained import get_model
import numpy as np
import torch

DEFAULT_SEPARATION_DEVICE = "cpu"
DEFAULT_SEPARATION_MODEL = "htdemucs"
VALID_SEPARATION_TARGETS = ("bass", "drums", "other", "vocals")


@dataclass(frozen=True)
class StemSeparationResult:
    target_stem: str
    model_name: str
    device: str
    output_root: Path
    analyzed_audio_path: Path
    related_artifacts: tuple[str, ...]


def run_stem_separation(
    input_path: Path,
    *,
    target_stem: str,
    model_name: str = DEFAULT_SEPARATION_MODEL,
    output_dir: str | Path | None = None,
    device: str = DEFAULT_SEPARATION_DEVICE,
) -> StemSeparationResult:
    normalized_target_stem = _normalized_required_option(target_stem, option_name="target_stem")
    normalized_model_name = _normalized_required_option(model_name, option_name="model_name")
    normalized_device = _normalized_required_option(device, option_name="device")
    if normalized_target_stem not in VALID_SEPARATION_TARGETS:
        allowed = ", ".join(VALID_SEPARATION_TARGETS)
        raise ValueError(f"target_stem must be one of: {allowed}")

    output_root = Path(output_dir) if output_dir is not None else input_path.parent / ".rwif-stems"
    output_root.mkdir(parents=True, exist_ok=True)

    model = get_model(normalized_model_name)
    try:
        model.to(normalized_device)
    except Exception as exc:
        raise ValueError(f"Demucs stem separation failed to move model to device '{normalized_device}': {exc}") from exc
    ffmpeg_path = which("ffmpeg")
    if ffmpeg_path is None:
        raise ValueError("ffmpeg is required for Demucs stem separation")

    samples = _decode_audio_for_demucs(
        input_path,
        ffmpeg_path=ffmpeg_path,
        sample_rate_hz=int(model.samplerate),
        channel_count=int(model.audio_channels),
    )
    mix = torch.from_numpy(samples.T).unsqueeze(0).to(torch.float32)
    try:
        with torch.no_grad():
            separated = apply_model(model, mix, device=normalized_device, progress=False, num_workers=0)
    except Exception as exc:
        raise ValueError(f"Demucs stem separation failed during model inference: {exc}") from exc

    sources = separated[0].detach().cpu()
    source_names = list(getattr(model, "sources", []))
    if normalized_target_stem not in source_names:
        raise ValueError(
            f"Demucs model '{normalized_model_name}' does not expose target stem '{normalized_target_stem}'"
        )
    target_index = source_names.index(normalized_target_stem)

    model_output_dir = output_root / normalized_model_name / input_path.stem
    model_output_dir.mkdir(parents=True, exist_ok=True)
    analyzed_audio_path = model_output_dir / f"{normalized_target_stem}.wav"
    no_target_path = model_output_dir / f"no_{normalized_target_stem}.wav"

    target_audio = sources[target_index].numpy().T
    residual_audio = (mix[0].detach().cpu() - sources[target_index]).numpy().T
    _write_wav_float(analyzed_audio_path, target_audio, sample_rate_hz=int(model.samplerate))
    _write_wav_float(no_target_path, residual_audio, sample_rate_hz=int(model.samplerate))

    related_artifacts = [str(analyzed_audio_path)]
    if no_target_path.exists():
        related_artifacts.append(str(no_target_path))

    return StemSeparationResult(
        target_stem=normalized_target_stem,
        model_name=normalized_model_name,
        device=normalized_device,
        output_root=output_root,
        analyzed_audio_path=analyzed_audio_path,
        related_artifacts=tuple(related_artifacts),
    )


def _normalized_required_option(value: str, *, option_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{option_name} must be a string")
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{option_name} must be non-empty")
    return normalized_value


def _decode_audio_for_demucs(
    input_path: Path,
    *,
    ffmpeg_path: str,
    sample_rate_hz: int,
    channel_count: int,
) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        temp_wav_path = Path(handle.name)
    try:
        command = [
            ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            str(sample_rate_hz),
            "-ac",
            str(channel_count),
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            str(temp_wav_path),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "ffmpeg decode failed"
            raise ValueError(stderr)
        samples, observed_sample_rate_hz = _load_wav_pcm(temp_wav_path)
    finally:
        temp_wav_path.unlink(missing_ok=True)

    if observed_sample_rate_hz != sample_rate_hz:
        raise ValueError(
            f"Demucs decode pipeline expected {sample_rate_hz} Hz audio but observed {observed_sample_rate_hz} Hz"
        )
    if samples.shape[1] != channel_count:
        raise ValueError(
            f"Demucs decode pipeline expected {channel_count} channels but observed {samples.shape[1]} channels"
        )
    return samples.astype(np.float32, copy=False)


def _load_wav_pcm(input_path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(input_path), "rb") as handle:
        observed_channel_count = handle.getnchannels()
        sample_rate_hz = handle.getframerate()
        frame_count = handle.getnframes()
        sample_width = handle.getsampwidth()
        raw_frames = handle.readframes(frame_count)

    if observed_channel_count <= 0 or sample_rate_hz <= 0:
        raise ValueError("wav input must declare positive channels and sample rate")
    if sample_width == 1:
        pcm = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32)
        pcm = (pcm - 128.0) / 128.0
    elif sample_width == 2:
        pcm = np.frombuffer(raw_frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        pcm = np.frombuffer(raw_frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported wav sample width: {sample_width}")
    if pcm.size % observed_channel_count != 0:
        raise ValueError("wav frame data does not align with channel count")
    return pcm.reshape(-1, observed_channel_count), sample_rate_hz


def _write_wav_float(path: Path, samples: np.ndarray, *, sample_rate_hz: int) -> None:
    clipped_samples = np.clip(samples, -1.0, 1.0)
    pcm = np.round(clipped_samples * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(int(samples.shape[1]))
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(pcm.tobytes())
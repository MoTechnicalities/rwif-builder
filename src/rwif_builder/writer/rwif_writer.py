from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import struct
from typing import Any

import numpy as np

from ..manifest.models import BuilderManifest
from ..normalize.records import ChunkRecord

RWIF_MAGIC = b"RWIFACT1"
RWIF_HEADER_STRUCT = struct.Struct("<8sI")
RWIF_UNIT_STRUCT = struct.Struct("<Id")
MEMORY_METADATA_KEY = "rwif_memory_store"
SEMANTIC_MEMORY_METADATA_KEY = "rwif_semantic_memory"
BUILDER_MANIFEST_KEY = "rwif_builder_manifest"


@dataclass(frozen=True)
class AtomicWaveUnit:
    frequency_index: int
    amplitude: float


@dataclass(frozen=True)
class WaveState:
    vector_length: int
    units: tuple[AtomicWaveUnit, ...]
    label: str | None = None
    centered_norm: float = 0.0
    original_norm: float = 0.0
    top_k: int = 0
    metadata: dict[str, Any] | None = None

    def to_header_entry(self, awu_offset: int) -> dict[str, Any]:
        return {
            "label": self.label,
            "vector_length": self.vector_length,
            "centered_norm": self.centered_norm,
            "original_norm": self.original_norm,
            "top_k": self.top_k,
            "metadata": dict(self.metadata or {}),
            "awu_offset": awu_offset,
            "awu_count": len(self.units),
        }


@dataclass(frozen=True)
class WaveLibrary:
    states: tuple[WaveState, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LoadedArtifact:
    library: WaveLibrary
    manifest: dict[str, Any]


@lru_cache(maxsize=32)
def _dct_basis(vector_length: int) -> np.ndarray:
    if vector_length <= 0:
        raise ValueError("vector_length must be positive")
    positions = np.arange(vector_length, dtype=np.float64)
    frequencies = np.arange(vector_length, dtype=np.float64)[:, None]
    basis = np.cos(np.pi / vector_length * (positions + 0.5) * frequencies)
    basis[0, :] *= np.sqrt(1.0 / vector_length)
    if vector_length > 1:
        basis[1:, :] *= np.sqrt(2.0 / vector_length)
    return basis


def _dct(vector: np.ndarray) -> np.ndarray:
    return _dct_basis(int(vector.shape[0])) @ vector


def estimate_background(activations: np.ndarray) -> np.ndarray:
    matrix = np.asarray(activations, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("activations must be a 2D matrix with at least one row")
    return np.mean(matrix, axis=0)


def encode_activation(
    activation: np.ndarray,
    *,
    background: np.ndarray | None = None,
    top_k: int = 128,
    label: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> WaveState:
    vector = np.asarray(activation, dtype=np.float64)
    if vector.ndim != 1:
        raise ValueError("activation must be a 1D vector")
    centered = vector.copy()
    if background is not None:
        background_vector = np.asarray(background, dtype=np.float64)
        if background_vector.shape != vector.shape:
            raise ValueError("background must have the same shape as activation")
        centered = centered - background_vector
    coefficients = _dct(centered)
    keep_count = min(max(1, top_k), coefficients.shape[0])
    top_indices = np.argpartition(np.abs(coefficients), -keep_count)[-keep_count:]
    ordered_indices = sorted(top_indices.tolist(), key=lambda index: abs(coefficients[index]), reverse=True)
    units = tuple(AtomicWaveUnit(frequency_index=index, amplitude=float(coefficients[index])) for index in ordered_indices)
    return WaveState(
        vector_length=int(vector.shape[0]),
        units=units,
        label=label,
        centered_norm=float(np.linalg.norm(centered)),
        original_norm=float(np.linalg.norm(vector)),
        top_k=keep_count,
        metadata=dict(metadata or {}),
    )


def save_semantic_memory_artifact(
    path: str | Path,
    *,
    chunks: list[ChunkRecord],
    activations: np.ndarray,
    background: np.ndarray,
    manifest: BuilderManifest,
    source_model: str,
    top_k_waves: int,
) -> None:
    if len(chunks) != int(activations.shape[0]):
        raise ValueError("chunk count does not match activation count")
    states: list[WaveState] = []
    for chunk, activation in zip(chunks, activations, strict=True):
        semantic_payload = {
            "memory_id": chunk.memory_id,
            "revision": 1,
            "title": chunk.title,
            "canonical_text": chunk.canonical_text,
            "kind": "document_chunk",
            "summary": chunk.canonical_text[:200],
            "facts": [],
            "tags": list(chunk.tags),
            "relations": [],
            "provenance": [
                {
                    "source_id": chunk.source_document.relative_path,
                    "source_type": chunk.source_document.source_type,
                    "locator": chunk.locator,
                }
            ],
            "status": "active",
            "source_model": source_model,
            "metadata": {
                "chunk_id": chunk.chunk_id,
                "relative_path": chunk.source_document.relative_path,
                "source_sha256": chunk.source_document.sha256,
                **chunk.metadata,
            },
        }
        record_metadata = {
            **chunk.metadata,
            SEMANTIC_MEMORY_METADATA_KEY: semantic_payload,
        }
        state_metadata = {
            MEMORY_METADATA_KEY: {
                "record_id": f"{chunk.memory_id}@r000001",
                "text": chunk.canonical_text,
                "metadata": record_metadata,
                "source": chunk.source_document.relative_path,
            }
        }
        states.append(
            encode_activation(
                np.asarray(activation, dtype=np.float64),
                background=background,
                top_k=top_k_waves,
                label=f"{chunk.memory_id}@r1",
                metadata=state_metadata,
            )
        )
    library = WaveLibrary(
        states=tuple(states),
        metadata={
            "background": np.asarray(background, dtype=np.float64).tolist(),
            "format": "rwif_semantic_memory",
            "semantic_memory_version": 1,
            BUILDER_MANIFEST_KEY: manifest.to_payload(),
        },
    )
    save_wave_library(path, library)


def save_wave_library(path: str | Path, library: WaveLibrary) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    awu_offset = 0
    state_headers: list[dict[str, Any]] = []
    for state in library.states:
        state_headers.append(state.to_header_entry(awu_offset))
        awu_offset += len(state.units)
    header = {
        "version": 1,
        "library_metadata": library.metadata,
        "states": state_headers,
    }
    header_bytes = json.dumps(header, separators=(",", ":"), ensure_ascii=True, sort_keys=True).encode("utf-8")
    with output_path.open("wb") as handle:
        handle.write(RWIF_HEADER_STRUCT.pack(RWIF_MAGIC, len(header_bytes)))
        handle.write(header_bytes)
        for state in library.states:
            for unit in state.units:
                handle.write(RWIF_UNIT_STRUCT.pack(unit.frequency_index, unit.amplitude))


def load_wave_library(path: str | Path) -> WaveLibrary:
    input_path = Path(path)
    with input_path.open("rb") as handle:
        prefix = handle.read(RWIF_HEADER_STRUCT.size)
        if len(prefix) != RWIF_HEADER_STRUCT.size:
            raise ValueError("file is too small to be a RWIF artifact")
        magic, header_size = RWIF_HEADER_STRUCT.unpack(prefix)
        if magic != RWIF_MAGIC:
            raise ValueError("not a RWIF activation-core file")
        header = json.loads(handle.read(header_size).decode("utf-8"))
        states: list[WaveState] = []
        for state_header in header["states"]:
            units: list[AtomicWaveUnit] = []
            for _ in range(state_header["awu_count"]):
                unit_bytes = handle.read(RWIF_UNIT_STRUCT.size)
                if len(unit_bytes) != RWIF_UNIT_STRUCT.size:
                    raise ValueError("RWIF artifact ended unexpectedly while reading wave units")
                index, amplitude = RWIF_UNIT_STRUCT.unpack(unit_bytes)
                units.append(AtomicWaveUnit(frequency_index=index, amplitude=amplitude))
            states.append(
                WaveState(
                    vector_length=int(state_header["vector_length"]),
                    units=tuple(units),
                    label=state_header.get("label"),
                    centered_norm=float(state_header.get("centered_norm", 0.0)),
                    original_norm=float(state_header.get("original_norm", 0.0)),
                    top_k=int(state_header.get("top_k", len(units))),
                    metadata=dict(state_header.get("metadata", {})),
                )
            )
    return WaveLibrary(states=tuple(states), metadata=dict(header.get("library_metadata", {})))


def load_semantic_memory_artifact(path: str | Path) -> LoadedArtifact:
    library = load_wave_library(path)
    manifest = dict(library.metadata.get(BUILDER_MANIFEST_KEY, {}))
    return LoadedArtifact(library=library, manifest=manifest)

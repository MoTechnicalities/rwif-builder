from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from rwif_builder.writer.rwif_writer import AtomicWaveUnit
from rwif_builder.writer.rwif_writer import WaveLibrary
from rwif_builder.writer.rwif_writer import WaveState
from rwif_builder.writer.rwif_writer import save_wave_library


class ARWIFIntegrationTest(unittest.TestCase):
    def test_arwif_validate_and_render(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            artifact_path = tmp_dir / "demo.arwif"
            wav_path = tmp_dir / "demo.wav"

            save_wave_library(
                artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(
                                AtomicWaveUnit(261, 0.8),
                                AtomicWaveUnit(330, 0.7),
                                AtomicWaveUnit(392, 0.6),
                            ),
                            label="CEG",
                            centered_norm=0.0,
                            original_norm=0.0,
                            top_k=3,
                            metadata={"duration_seconds": 0.25},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "title": "C major triad",
                    },
                ),
            )

            validate_payload = self._run_json(repo_root, "arwif-validate", str(artifact_path), "--json")
            self.assertTrue(validate_payload["is_valid"], validate_payload)

            render_payload = self._run_json(
                repo_root,
                "arwif-render",
                str(artifact_path),
                str(wav_path),
                "--json",
            )
            self.assertTrue(wav_path.exists())
            self.assertEqual(render_payload["sample_rate_hz"], 8000)
            self.assertEqual(render_payload["segment_count"], 1)
            with wave.open(str(wav_path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 8000)
                self.assertGreater(handle.getnframes(), 0)

    def test_arwif_validate_legacy_mode(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            artifact_path = tmp_dir / "legacy.arwif"

            save_wave_library(
                artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=384,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.8), AtomicWaveUnit(392, 0.8)),
                            label="legacy",
                            metadata={},
                        ),
                    ),
                    metadata={"title": "Legacy triad"},
                ),
            )

            strict_payload = self._run_json(repo_root, "arwif-validate", str(artifact_path), "--json", allow_failure=True)
            self.assertFalse(strict_payload["is_valid"])

            legacy_payload = self._run_json(repo_root, "arwif-validate", str(artifact_path), "--legacy", "--json")
            self.assertTrue(legacy_payload["is_valid"], legacy_payload)
            self.assertGreater(len(legacy_payload["warnings"]), 0)

    def _run(self, repo_root: Path, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-m", "rwif_builder.cli", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(repo_root / "src")},
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result.stdout

    def _run_json(self, repo_root: Path, *args: str, allow_failure: bool = False) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, "-m", "rwif_builder.cli", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(repo_root / "src")},
        )
        if result.returncode != 0 and not allow_failure:
            self.fail(result.stderr or result.stdout)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
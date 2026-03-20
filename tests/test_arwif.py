from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import yaml

from rwif_builder.writer.rwif_writer import AtomicWaveUnit
from rwif_builder.writer.rwif_writer import WaveLibrary
from rwif_builder.writer.rwif_writer import WaveState
from rwif_builder.writer.rwif_writer import save_wave_library


class ARWIFIntegrationTest(unittest.TestCase):
    def test_arwif_build_validate_and_render(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "demo.arwif.yaml"
            artifact_path = tmp_dir / "demo.arwif"
            wav_path = tmp_dir / "demo.wav"
            spec_path.write_text(
                """
title: Built triad
sample_rate_hz: 8000
default_duration_seconds: 0.25
states:
  - label: intro
    duration_seconds: 0.1
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
  - label: sustain
    oscillators:
      - hz: 392
        amplitude: 0.6
""".strip()
                + "\n",
                encoding="utf-8",
            )

            build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(spec_path),
                "--output",
                str(artifact_path),
                "--json",
            )
            self.assertTrue(artifact_path.exists())
            self.assertTrue(build_payload["is_valid"], build_payload)
            self.assertTrue(build_payload["spec_is_valid"], build_payload)
            self.assertEqual(build_payload["state_count"], 2)
            self.assertEqual(build_payload["oscillator_count"], 3)

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(spec_path), "--json")
            self.assertTrue(spec_payload["is_valid"], spec_payload)
            self.assertEqual(spec_payload["stats"]["state_count"], 2)
            self.assertEqual(spec_payload["stats"]["oscillator_count"], 3)

            validate_payload = self._run_json(repo_root, "arwif-validate", str(artifact_path), "--json")
            self.assertTrue(validate_payload["is_valid"], validate_payload)

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
            self.assertTrue(inspect_payload["is_valid"], inspect_payload)
            self.assertEqual(inspect_payload["state_count"], 2)
            self.assertEqual(inspect_payload["oscillator_count"], 3)
            self.assertEqual(inspect_payload["states"][0]["label"], "intro")

            render_payload = self._run_json(repo_root, "arwif-render", str(artifact_path), str(wav_path), "--json")
            self.assertEqual(render_payload["segment_count"], 2)
            self.assertTrue(wav_path.exists())

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

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
            self.assertTrue(inspect_payload["is_valid"], inspect_payload)
            self.assertEqual(inspect_payload["state_labels"], ["CEG"])
            self.assertEqual(inspect_payload["states"][0]["max_frequency_hz"], 392)

            render_payload = self._run_json(repo_root, "arwif-render", str(artifact_path), str(wav_path), "--json")
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

            strict_inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json", allow_failure=True)
            self.assertFalse(strict_inspect_payload["is_valid"])

            legacy_payload = self._run_json(repo_root, "arwif-validate", str(artifact_path), "--legacy", "--json")
            self.assertTrue(legacy_payload["is_valid"], legacy_payload)
            self.assertGreater(len(legacy_payload["warnings"]), 0)

            legacy_inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--legacy", "--json")
            self.assertTrue(legacy_inspect_payload["is_valid"], legacy_inspect_payload)
            self.assertTrue(legacy_inspect_payload["legacy_mode"])

    def test_arwif_diff_reports_metadata_and_state_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left.arwif"
            right_path = tmp_dir / "right.arwif"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="CE",
                            top_k=2,
                            metadata={"duration_seconds": 0.5},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.5,
                        "normalize": True,
                    },
                ),
            )

            save_wave_library(
                right_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(392, 0.6)),
                            label="CE",
                            top_k=2,
                            metadata={"duration_seconds": 1.0},
                        ),
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="C5",
                            top_k=1,
                            metadata={"duration_seconds": 0.25},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 1.0,
                        "normalize": False,
                    },
                ),
            )

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(diff_payload["left_valid"], diff_payload)
            self.assertTrue(diff_payload["right_valid"], diff_payload)
            self.assertEqual(diff_payload["change_summary"]["added_states"], 1)
            self.assertEqual(diff_payload["change_summary"]["changed_states"], 1)
            self.assertIn("C5", diff_payload["added_states"])
            self.assertIn("CE", diff_payload["changed_states"])
            self.assertIn("sample_rate_hz", diff_payload["metadata_changes"])
            self.assertEqual(diff_payload["oscillator_count_delta"], 1)

    def test_arwif_validate_spec_reports_field_errors(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid.yaml"
            artifact_path = tmp_dir / "invalid.arwif"
            spec_path.write_text(
                """
title: 123
sample_rate_hz: 0
default_duration_seconds: -1
normalize: maybe
states:
  - label: ok
    oscillators:
      - hz: 5000
        amplitude: bad
""".strip()
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(spec_path), "--json", allow_failure=True)
            self.assertFalse(spec_payload["is_valid"])
            self.assertIn("title must be a string", spec_payload["errors"])
            self.assertIn("sample_rate_hz must be a positive integer", spec_payload["errors"])
            self.assertIn("default_duration_seconds must be a positive number", spec_payload["errors"])
            self.assertIn("normalize must be a boolean", spec_payload["errors"])

            build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(spec_path),
                "--output",
                str(artifact_path),
                "--json",
                allow_failure=True,
            )
            self.assertFalse(build_payload["is_valid"])
            self.assertFalse(artifact_path.exists())
            self.assertIn("title must be a string", build_payload["errors"])

    def test_arwif_export_import_round_trip(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            source_spec_path = tmp_dir / "source.yaml"
            source_artifact_path = tmp_dir / "source.arwif"
            exported_spec_path = tmp_dir / "exported.yaml"
            imported_artifact_path = tmp_dir / "imported.arwif"

            source_spec_path.write_text(
                """
title: Round trip triad
description: Export import round trip fixture.
sample_rate_hz: 12000
default_duration_seconds: 0.5
default_attack_ms: 7.0
default_release_ms: 9.0
normalize: false
metadata:
  fixture: round-trip
states:
  - label: alpha
    duration_seconds: 0.5
    gain: 0.8
    metadata:
      note: alpha-state
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 392
        amplitude: 0.4
  - label: beta
    duration_seconds: 0.25
    phase_radians: 0.5
    oscillators:
      - hz: 523
        amplitude: 0.2
""".strip()
                + "\n",
                encoding="utf-8",
            )

            build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(source_spec_path),
                "--output",
                str(source_artifact_path),
                "--json",
            )
            self.assertTrue(build_payload["is_valid"], build_payload)

            export_payload = self._run_json(
                repo_root,
                "arwif-export",
                str(source_artifact_path),
                str(exported_spec_path),
                "--json",
            )
            self.assertTrue(export_payload["is_valid"], export_payload)
            self.assertTrue(exported_spec_path.exists())

            exported_document = yaml.safe_load(exported_spec_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_document["title"], "Round trip triad")
            self.assertEqual(exported_document["metadata"]["fixture"], "round-trip")
            self.assertEqual(exported_document["states"][0]["metadata"]["note"], "alpha-state")
            self.assertEqual(exported_document["states"][1]["oscillators"][0]["hz"], 523)

            import_payload = self._run_json(
                repo_root,
                "arwif-import",
                "--spec",
                str(exported_spec_path),
                "--output",
                str(imported_artifact_path),
                "--json",
            )
            self.assertTrue(import_payload["is_valid"], import_payload)
            self.assertTrue(import_payload["imported"])

            diff_payload = self._run_json(
                repo_root,
                "arwif-diff",
                str(source_artifact_path),
                str(imported_artifact_path),
                "--json",
            )
            self.assertEqual(diff_payload["change_summary"]["metadata_fields_changed"], 0)
            self.assertEqual(diff_payload["change_summary"]["added_states"], 0)
            self.assertEqual(diff_payload["change_summary"]["removed_states"], 0)
            self.assertEqual(diff_payload["change_summary"]["changed_states"], 0)

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
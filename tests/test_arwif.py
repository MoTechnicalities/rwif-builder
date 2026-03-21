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
                            metadata={
                                "duration_seconds": 0.5,
                                "channel_gains": {"L": 1.0, "R": 0.25},
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "channel_layout": "stereo",
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
                            metadata={
                                "duration_seconds": 1.0,
                                "channel_gains": {"L": 0.2, "R": 1.0},
                            },
                        ),
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="C5",
                            top_k=1,
                            metadata={
                                "duration_seconds": 0.25,
                                "channel_gains": {"L": 0.6, "R": 0.6},
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "channel_layout": "stereo",
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
            self.assertIn("channel_gains", diff_payload["state_changes"]["CE"]["metadata_changes"])
            self.assertEqual(
                diff_payload["state_changes"]["CE"]["metadata_changes"]["channel_gains"]["right"]["R"],
                1.0,
            )
            self.assertEqual(diff_payload["left_spatial_summary"]["channel_layout"], "stereo")
            self.assertEqual(diff_payload["right_spatial_summary"]["active_channels"], ["L", "R"])
            self.assertEqual(diff_payload["spatial_changes"]["states_with_channel_gains_delta"], 1)
            self.assertFalse(diff_payload["spatial_changes"]["channel_layout_changed"])

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

    def test_arwif_spatial_commands_do_not_crash_on_invalid_channel_gains(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            artifact_path = tmp_dir / "invalid-channel-gains.arwif"
            export_path = tmp_dir / "invalid-channel-gains.yaml"

            save_wave_library(
                artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=256,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="broken",
                            metadata={"channel_gains": "not-a-mapping"},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "channel_layout": "stereo",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                    },
                ),
            )

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json", allow_failure=True)
            self.assertFalse(inspect_payload["is_valid"], inspect_payload)
            self.assertIn("state 0 channel_gains must be a mapping", inspect_payload["errors"])
            self.assertEqual(inspect_payload["spatial_summary"]["states_with_channel_gains"], 0)

            export_payload = self._run_json(
                repo_root,
                "arwif-export",
                str(artifact_path),
                str(export_path),
                "--json",
                allow_failure=True,
            )
            self.assertFalse(export_payload["is_valid"], export_payload)
            self.assertIn("state 0 channel_gains must be a mapping", export_payload["errors"])
            exported_document = yaml.safe_load(export_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_document["states"][0]["channel_gains"], {})

            diff_payload = self._run_json(
                repo_root,
                "arwif-diff",
                str(artifact_path),
                str(artifact_path),
                "--json",
                allow_failure=True,
            )
            self.assertFalse(diff_payload["left_valid"], diff_payload)
            self.assertFalse(diff_payload["right_valid"], diff_payload)
            self.assertEqual(diff_payload["left_spatial_summary"]["states_with_channel_gains"], 0)
            self.assertEqual(diff_payload["right_spatial_summary"]["states_with_channel_gains"], 0)

    def test_arwif_normalize_legacy_artifact(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            legacy_artifact_path = tmp_dir / "legacy.arwif"
            normalized_spec_path = tmp_dir / "legacy.normalized.yaml"
            normalized_artifact_path = tmp_dir / "legacy.normalized.arwif"
            report_path = tmp_dir / "legacy.normalized.report.json"
            assumptions_path = tmp_dir / "legacy.normalized.assumptions.json"

            save_wave_library(
                legacy_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=384,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.8), AtomicWaveUnit(392, 0.8)),
                            label="legacy",
                            metadata={"note": "prototype"},
                        ),
                    ),
                    metadata={"title": "Legacy triad", "prototype_source": "pre-spec"},
                ),
            )

            normalize_payload = self._run_json(
                repo_root,
                "arwif-normalize",
                str(legacy_artifact_path),
                "--spec",
                str(normalized_spec_path),
                "--output",
                str(normalized_artifact_path),
                "--report",
                str(report_path),
                "--assumptions",
                str(assumptions_path),
                "--json",
            )
            self.assertTrue(normalize_payload["normalized"], normalize_payload)
            self.assertTrue(normalize_payload["legacy_mode"], normalize_payload)
            self.assertTrue(normalized_spec_path.exists())
            self.assertTrue(normalized_artifact_path.exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(assumptions_path.exists())
            self.assertTrue(normalize_payload["output_is_valid"], normalize_payload)
            self.assertIn("sample_rate_hz", normalize_payload["injected_defaults"])
            self.assertIn("default_duration_seconds", normalize_payload["injected_defaults"])
            self.assertEqual(normalize_payload["report_format"], "json")
            self.assertEqual(normalize_payload["report_output"], str(report_path))
            self.assertEqual(normalize_payload["assumptions_format"], "json")
            self.assertEqual(normalize_payload["assumptions_output"], str(assumptions_path))
            self.assertGreater(normalize_payload["assumption_count"], 0)

            normalized_document = yaml.safe_load(normalized_spec_path.read_text(encoding="utf-8"))
            self.assertEqual(normalized_document["title"], "Legacy triad")
            self.assertEqual(normalized_document["sample_rate_hz"], 48000)
            self.assertEqual(normalized_document["default_duration_seconds"], 1.0)
            self.assertEqual(normalized_document["metadata"]["prototype_source"], "pre-spec")
            self.assertEqual(normalized_document["states"][0]["metadata"]["note"], "prototype")

            report_document = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["report_version"], 1)
            self.assertEqual(report_document["artifact"], str(legacy_artifact_path))
            self.assertEqual(report_document["normalized_spec_output"], str(normalized_spec_path))
            self.assertEqual(report_document["rebuilt_artifact_output"], str(normalized_artifact_path))
            self.assertTrue(report_document["source_validation"]["legacy_mode"])
            self.assertIn("sample_rate_hz", report_document["normalization"]["injected_defaults"])
            self.assertEqual(
                report_document["normalization"]["preserved_library_metadata"]["prototype_source"],
                "pre-spec",
            )
            self.assertEqual(
                report_document["normalization"]["preserved_state_metadata"][0]["preserved_metadata"]["note"],
                "prototype",
            )
            self.assertTrue(report_document["normalized_spec_validation"]["is_valid"])
            self.assertTrue(report_document["rebuilt_artifact_validation"]["is_valid"])
            self.assertEqual(report_document["normalized_document"]["metadata"]["prototype_source"], "pre-spec")

            assumptions_document = json.loads(assumptions_path.read_text(encoding="utf-8"))
            self.assertEqual(assumptions_document["manifest_version"], 1)
            self.assertEqual(assumptions_document["artifact"], str(legacy_artifact_path))
            self.assertEqual(assumptions_document["normalized_spec_output"], str(normalized_spec_path))
            self.assertEqual(assumptions_document["rebuilt_artifact_output"], str(normalized_artifact_path))
            self.assertTrue(assumptions_document["legacy_mode"])
            self.assertEqual(
                assumptions_document["summary"]["assumption_count"],
                normalize_payload["assumption_count"],
            )
            self.assertGreaterEqual(assumptions_document["summary"]["default_injections"], 2)
            self.assertEqual(assumptions_document["summary"]["preserved_library_metadata_fields"], 1)
            self.assertEqual(assumptions_document["summary"]["preserved_state_metadata_fields"], 1)
            assumption_kinds = {entry["kind"] for entry in assumptions_document["assumptions"]}
            self.assertTrue(
                {
                    "default_injected",
                    "library_metadata_preserved",
                    "state_metadata_preserved",
                    "source_warning",
                }.issubset(assumption_kinds)
            )
            self.assertIn(
                {
                    "kind": "library_metadata_preserved",
                    "field": "prototype_source",
                    "value": "pre-spec",
                },
                assumptions_document["assumptions"],
            )
            self.assertIn(
                {
                    "kind": "state_metadata_preserved",
                    "state_index": 0,
                    "state_label": "legacy",
                    "field": "note",
                    "value": "prototype",
                },
                assumptions_document["assumptions"],
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(normalized_spec_path), "--json")
            self.assertTrue(spec_payload["is_valid"], spec_payload)

            validate_payload = self._run_json(repo_root, "arwif-validate", str(normalized_artifact_path), "--json")
            self.assertTrue(validate_payload["is_valid"], validate_payload)

    def test_arwif_batch_normalize_legacy_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_artifact_path = tmp_dir / "alpha.arwif"
            second_artifact_path = tmp_dir / "beta.arwif"
            spec_dir = tmp_dir / "specs"
            output_dir = tmp_dir / "artifacts"
            report_dir = tmp_dir / "reports"
            assumptions_dir = tmp_dir / "assumptions"
            batch_report_path = tmp_dir / "batch-normalize-report.yaml"

            save_wave_library(
                first_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=384,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.8), AtomicWaveUnit(392, 0.8)),
                            label="alpha",
                            metadata={"note": "first"},
                        ),
                    ),
                    metadata={"title": "Alpha triad", "prototype_source": "batch-a"},
                ),
            )

            save_wave_library(
                second_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(440, 0.7), AtomicWaveUnit(550, 0.5)),
                            label="beta",
                            metadata={"note": "second"},
                        ),
                    ),
                    metadata={"title": "Beta dyad", "prototype_source": "batch-b"},
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-normalize",
                str(first_artifact_path),
                str(second_artifact_path),
                "--spec-dir",
                str(spec_dir),
                "--output-dir",
                str(output_dir),
                "--report-dir",
                str(report_dir),
                "--assumptions-dir",
                str(assumptions_dir),
                "--output",
                str(batch_report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["artifacts_processed"], 2)
            self.assertEqual(batch_payload["normalized_count"], 2)
            self.assertEqual(batch_payload["failed_count"], 0)
            self.assertEqual(batch_payload["format"], "yaml")
            self.assertEqual(batch_payload["spec_dir"], str(spec_dir))
            self.assertEqual(batch_payload["output_dir"], str(output_dir))
            self.assertEqual(batch_payload["report_dir"], str(report_dir))
            self.assertEqual(batch_payload["assumptions_dir"], str(assumptions_dir))
            self.assertEqual(batch_payload["report_output"], str(batch_report_path))
            self.assertEqual(batch_payload["report_format"], "yaml")
            self.assertGreater(batch_payload["total_assumption_count"], 0)
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = yaml.safe_load(batch_report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["artifacts_processed"], 2)
            self.assertEqual(persisted_report["normalized_count"], 2)

            expected_specs = {
                spec_dir / "alpha.normalized.yaml",
                spec_dir / "beta.normalized.yaml",
            }
            expected_outputs = {
                output_dir / "alpha.normalized.arwif",
                output_dir / "beta.normalized.arwif",
            }
            expected_reports = {
                report_dir / "alpha.normalized.report.json",
                report_dir / "beta.normalized.report.json",
            }
            expected_assumptions = {
                assumptions_dir / "alpha.normalized.assumptions.json",
                assumptions_dir / "beta.normalized.assumptions.json",
            }

            for path in expected_specs | expected_outputs | expected_reports | expected_assumptions:
                self.assertTrue(path.exists(), path)

            normalized_artifacts = {result["artifact"] for result in batch_payload["results"]}
            self.assertEqual(
                normalized_artifacts,
                {str(first_artifact_path), str(second_artifact_path)},
            )

            for result in batch_payload["results"]:
                self.assertTrue(result["normalized"], result)
                self.assertTrue(result["legacy_mode"], result)
                self.assertTrue(result["output_is_valid"], result)
                self.assertEqual(result["report_format"], "json")
                self.assertEqual(result["assumptions_format"], "json")
                self.assertGreater(result["assumption_count"], 0)

    def test_arwif_batch_build_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_spec_path = tmp_dir / "alpha.yaml"
            second_spec_path = tmp_dir / "beta.yaml"
            output_dir = tmp_dir / "artifacts"
            report_path = tmp_dir / "batch-build-report.json"

            first_spec_path.write_text(
                """
title: Alpha chord
sample_rate_hz: 8000
default_duration_seconds: 0.25
states:
  - label: alpha
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
""".strip()
                + "\n",
                encoding="utf-8",
            )

            second_spec_path.write_text(
                """
title: Beta chord
sample_rate_hz: 12000
default_duration_seconds: 0.5
states:
  - label: beta
    duration_seconds: 0.5
    oscillators:
      - hz: 392
        amplitude: 0.6
      - hz: 523
        amplitude: 0.4
      - hz: 659
        amplitude: 0.2
""".strip()
                + "\n",
                encoding="utf-8",
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-build",
                str(first_spec_path),
                str(second_spec_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["specs_processed"], 2)
            self.assertEqual(batch_payload["built_count"], 2)
            self.assertEqual(batch_payload["failed_count"], 0)
            self.assertEqual(batch_payload["output_dir"], str(output_dir))
            self.assertEqual(batch_payload["total_oscillator_count"], 5)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "json")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["specs_processed"], 2)
            self.assertEqual(persisted_report["built_count"], 2)

            expected_artifacts = {
                output_dir / "alpha.arwif",
                output_dir / "beta.arwif",
            }
            for path in expected_artifacts:
                self.assertTrue(path.exists(), path)

            for result in batch_payload["results"]:
                self.assertTrue(result["is_valid"], result)
                self.assertTrue(result["spec_is_valid"], result)

            alpha_validate_payload = self._run_json(repo_root, "arwif-validate", str(output_dir / "alpha.arwif"), "--json")
            beta_validate_payload = self._run_json(repo_root, "arwif-validate", str(output_dir / "beta.arwif"), "--json")
            self.assertTrue(alpha_validate_payload["is_valid"], alpha_validate_payload)
            self.assertTrue(beta_validate_payload["is_valid"], beta_validate_payload)

    def test_arwif_batch_import_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_spec_path = tmp_dir / "alpha.yaml"
            second_spec_path = tmp_dir / "beta.yaml"
            output_dir = tmp_dir / "imports"
            report_path = tmp_dir / "batch-import-report.yaml"

            first_spec_path.write_text(
                """
title: Alpha imported chord
sample_rate_hz: 8000
default_duration_seconds: 0.25
states:
  - label: alpha
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
""".strip()
                + "\n",
                encoding="utf-8",
            )

            second_spec_path.write_text(
                """
title: Beta imported chord
sample_rate_hz: 12000
default_duration_seconds: 0.5
states:
  - label: beta
    duration_seconds: 0.5
    oscillators:
      - hz: 392
        amplitude: 0.6
      - hz: 523
        amplitude: 0.4
      - hz: 659
        amplitude: 0.2
""".strip()
                + "\n",
                encoding="utf-8",
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-import",
                str(first_spec_path),
                str(second_spec_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["specs_processed"], 2)
            self.assertEqual(batch_payload["imported_count"], 2)
            self.assertEqual(batch_payload["failed_count"], 0)
            self.assertEqual(batch_payload["output_dir"], str(output_dir))
            self.assertEqual(batch_payload["total_oscillator_count"], 5)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "yaml")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["specs_processed"], 2)
            self.assertEqual(persisted_report["imported_count"], 2)

            expected_artifacts = {
                output_dir / "alpha.arwif",
                output_dir / "beta.arwif",
            }
            for path in expected_artifacts:
                self.assertTrue(path.exists(), path)

            imported_artifacts = {result["artifact"] for result in batch_payload["results"]}
            self.assertEqual(imported_artifacts, {str(path) for path in expected_artifacts})

            for result in batch_payload["results"]:
                self.assertTrue(result["imported"], result)
                self.assertTrue(result["is_valid"], result)
                self.assertTrue(result["spec_is_valid"], result)

            alpha_validate_payload = self._run_json(repo_root, "arwif-validate", str(output_dir / "alpha.arwif"), "--json")
            beta_validate_payload = self._run_json(repo_root, "arwif-validate", str(output_dir / "beta.arwif"), "--json")
            self.assertTrue(alpha_validate_payload["is_valid"], alpha_validate_payload)
            self.assertTrue(beta_validate_payload["is_valid"], beta_validate_payload)

    def test_arwif_batch_validate_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_spec_path = tmp_dir / "valid.yaml"
            invalid_spec_path = tmp_dir / "invalid.yaml"
            report_path = tmp_dir / "batch-validate-spec-report.json"

            valid_spec_path.write_text(
                """
title: Valid batch spec
sample_rate_hz: 8000
default_duration_seconds: 0.25
states:
  - label: valid
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
""".strip()
                + "\n",
                encoding="utf-8",
            )

            invalid_spec_path.write_text(
                """
title: Invalid batch spec
sample_rate_hz: 0
states:
  - label: invalid
    oscillators:
      - hz: 261
        amplitude: 2.0
""".strip()
                + "\n",
                encoding="utf-8",
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-validate-spec",
                str(valid_spec_path),
                str(invalid_spec_path),
                "--output",
                str(report_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["specs_processed"], 2)
            self.assertEqual(batch_payload["valid_count"], 1)
            self.assertEqual(batch_payload["invalid_count"], 1)
            self.assertEqual(batch_payload["total_state_count"], 2)
            self.assertEqual(batch_payload["total_oscillator_count"], 2)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "json")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["specs_processed"], 2)
            self.assertEqual(persisted_report["invalid_count"], 1)

            valid_result = next(result for result in batch_payload["results"] if result["spec"] == str(valid_spec_path))
            invalid_result = next(result for result in batch_payload["results"] if result["spec"] == str(invalid_spec_path))

            self.assertTrue(valid_result["is_valid"], valid_result)
            self.assertFalse(invalid_result["is_valid"], invalid_result)
            self.assertIn("sample_rate_hz must be a positive integer", invalid_result["errors"])

    def test_arwif_batch_validate_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_artifact_path = tmp_dir / "valid.arwif"
            invalid_artifact_path = tmp_dir / "invalid.arwif"
            report_path = tmp_dir / "batch-validate-report.yaml"

            save_wave_library(
                valid_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="valid",
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
                        "title": "Valid batch artifact",
                    },
                ),
            )

            save_wave_library(
                invalid_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=256,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="invalid",
                            metadata={},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 0,
                        "default_duration_seconds": 0.25,
                    },
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-validate",
                str(valid_artifact_path),
                str(invalid_artifact_path),
                "--output",
                str(report_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["artifacts_processed"], 2)
            self.assertEqual(batch_payload["valid_count"], 1)
            self.assertEqual(batch_payload["invalid_count"], 1)
            self.assertFalse(batch_payload["allow_legacy"])
            self.assertEqual(batch_payload["total_state_count"], 2)
            self.assertEqual(batch_payload["total_oscillator_count"], 3)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "yaml")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["artifacts_processed"], 2)
            self.assertEqual(persisted_report["invalid_count"], 1)

            valid_result = next(result for result in batch_payload["results"] if result["artifact"] == str(valid_artifact_path))
            invalid_result = next(result for result in batch_payload["results"] if result["artifact"] == str(invalid_artifact_path))

            self.assertTrue(valid_result["is_valid"], valid_result)
            self.assertFalse(invalid_result["is_valid"], invalid_result)
            self.assertIn("library metadata 'sample_rate_hz' must be a positive integer", invalid_result["errors"])

    def test_arwif_batch_inspect_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_artifact_path = tmp_dir / "alpha.arwif"
            second_artifact_path = tmp_dir / "beta.arwif"
            report_path = tmp_dir / "batch-inspect-report.json"

            save_wave_library(
                first_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
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
                        "title": "Alpha batch inspect",
                    },
                ),
            )

            save_wave_library(
                second_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(392, 0.6),),
                            label="beta-intro",
                            metadata={"duration_seconds": 0.5},
                        ),
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta-outro",
                            metadata={"duration_seconds": 0.25},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 0.25,
                        "title": "Beta batch inspect",
                    },
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-inspect",
                str(first_artifact_path),
                str(second_artifact_path),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["artifacts_processed"], 2)
            self.assertEqual(batch_payload["valid_count"], 2)
            self.assertEqual(batch_payload["invalid_count"], 0)
            self.assertFalse(batch_payload["allow_legacy"])
            self.assertEqual(batch_payload["total_state_count"], 3)
            self.assertEqual(batch_payload["total_oscillator_count"], 4)
            self.assertEqual(batch_payload["max_frequency_hz"], 523)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "json")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["artifacts_processed"], 2)
            self.assertEqual(persisted_report["max_frequency_hz"], 523)

            inspected_artifacts = {result["artifact"] for result in batch_payload["results"]}
            self.assertEqual(inspected_artifacts, {str(first_artifact_path), str(second_artifact_path)})

            alpha_result = next(result for result in batch_payload["results"] if result["artifact"] == str(first_artifact_path))
            beta_result = next(result for result in batch_payload["results"] if result["artifact"] == str(second_artifact_path))

            self.assertEqual(alpha_result["state_count"], 1)
            self.assertEqual(alpha_result["oscillator_count"], 2)
            self.assertEqual(alpha_result["state_labels"], ["alpha"])
            self.assertEqual(beta_result["state_count"], 2)
            self.assertEqual(beta_result["max_frequency_hz"], 523)
            self.assertEqual(beta_result["state_labels"], ["beta-intro", "beta-outro"])

    def test_arwif_batch_render_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_artifact_path = tmp_dir / "alpha.arwif"
            second_artifact_path = tmp_dir / "beta.arwif"
            output_dir = tmp_dir / "renders"
            report_path = tmp_dir / "batch-render-report.yaml"

            save_wave_library(
                first_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
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
                        "title": "Alpha chord",
                    },
                ),
            )

            save_wave_library(
                second_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(392, 0.6),),
                            label="beta-intro",
                            metadata={"duration_seconds": 0.5},
                        ),
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta-outro",
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
                        "title": "Beta phrase",
                    },
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-render",
                str(first_artifact_path),
                str(second_artifact_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["artifacts_processed"], 2)
            self.assertEqual(batch_payload["rendered_count"], 2)
            self.assertEqual(batch_payload["failed_count"], 0)
            self.assertEqual(batch_payload["output_dir"], str(output_dir))
            self.assertAlmostEqual(batch_payload["total_duration_seconds"], 1.0, places=3)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "yaml")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["artifacts_processed"], 2)
            self.assertEqual(persisted_report["rendered_count"], 2)

            expected_outputs = {
                output_dir / "alpha.wav": 0.25,
                output_dir / "beta.wav": 0.75,
            }
            for path, expected_duration in expected_outputs.items():
                self.assertTrue(path.exists(), path)
                with wave.open(str(path), "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getframerate(), 8000)
                    self.assertAlmostEqual(handle.getnframes() / 8000.0, expected_duration, places=3)

            rendered_outputs = {result["output"] for result in batch_payload["results"]}
            self.assertEqual(rendered_outputs, {str(path) for path in expected_outputs})
            for result in batch_payload["results"]:
                self.assertTrue(result["rendered"], result)
                self.assertGreater(result["segment_count"], 0)
                self.assertGreater(result["duration_seconds"], 0.0)

    def test_arwif_batch_diff_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_alpha_path = tmp_dir / "left-alpha.arwif"
            right_alpha_path = tmp_dir / "right-alpha.arwif"
            left_beta_path = tmp_dir / "left-beta.arwif"
            right_beta_path = tmp_dir / "right-beta.arwif"
            report_path = tmp_dir / "batch-diff-report.json"

            save_wave_library(
                left_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
                            top_k=2,
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
                        "title": "Alpha left",
                    },
                ),
            )

            save_wave_library(
                right_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(392, 0.6)),
                            label="alpha",
                            top_k=2,
                            metadata={"duration_seconds": 0.5},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 0.5,
                        "title": "Alpha right",
                    },
                ),
            )

            save_wave_library(
                left_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            save_wave_library(
                right_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_alpha_path),
                str(left_beta_path),
                "--right",
                str(right_alpha_path),
                str(right_beta_path),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["pairs_compared"], 2)
            self.assertEqual(batch_payload["changed_pairs"], 1)
            self.assertEqual(batch_payload["unchanged_pairs"], 1)
            self.assertEqual(batch_payload["invalid_pairs"], 0)
            self.assertEqual(batch_payload["incompatible_pairs"], 0)
            self.assertEqual(batch_payload["total_metadata_fields_changed"], 3)
            self.assertEqual(batch_payload["total_changed_states"], 1)
            self.assertEqual(len(batch_payload["results"]), 2)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "json")
            self.assertTrue(report_path.exists())

            changed_result = next(result for result in batch_payload["results"] if result["pair_index"] == 0)
            unchanged_result = next(result for result in batch_payload["results"] if result["pair_index"] == 1)

            self.assertTrue(changed_result["pair_changed"], changed_result)
            self.assertEqual(changed_result["change_summary"]["metadata_fields_changed"], 3)
            self.assertEqual(changed_result["change_summary"]["changed_states"], 1)
            self.assertIn("alpha", changed_result["changed_states"])

            self.assertFalse(unchanged_result["pair_changed"], unchanged_result)
            self.assertEqual(unchanged_result["change_summary"]["metadata_fields_changed"], 0)
            self.assertEqual(unchanged_result["change_summary"]["changed_states"], 0)

            report_document = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["pairs_compared"], batch_payload["pairs_compared"])
            self.assertEqual(report_document["changed_pairs"], batch_payload["changed_pairs"])
            self.assertEqual(report_document["unchanged_pairs"], batch_payload["unchanged_pairs"])
            self.assertEqual(len(report_document["results"]), 2)

    def test_arwif_batch_diff_analyze_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_alpha_path = tmp_dir / "left-alpha.arwif"
            right_alpha_path = tmp_dir / "right-alpha.arwif"
            left_beta_path = tmp_dir / "left-beta.arwif"
            right_beta_path = tmp_dir / "right-beta.arwif"
            diff_report_path = tmp_dir / "batch-diff-report.json"
            analysis_report_path = tmp_dir / "batch-diff-analysis.yaml"

            save_wave_library(
                left_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
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
                        "title": "Alpha left",
                    },
                ),
            )

            save_wave_library(
                right_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(392, 0.6)),
                            label="alpha",
                            metadata={"duration_seconds": 0.5},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 0.5,
                        "title": "Alpha right",
                    },
                ),
            )

            save_wave_library(
                left_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            save_wave_library(
                right_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_alpha_path),
                str(left_beta_path),
                "--right",
                str(right_alpha_path),
                str(right_beta_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(
                repo_root,
                "arwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )

            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["analysis_input"], str(diff_report_path))
            self.assertEqual(analysis_payload["pairs_compared"], 2)
            self.assertEqual(analysis_payload["changed_pairs"], 1)
            self.assertEqual(analysis_payload["unchanged_pairs"], 1)
            self.assertEqual(analysis_payload["invalid_pairs"], 0)
            self.assertEqual(analysis_payload["incompatible_pairs"], 0)
            self.assertEqual(analysis_payload["states_changed_in_all_changed_pairs"], ["alpha"])
            self.assertEqual(
                analysis_payload["metadata_fields_changed_in_all_changed_pairs"],
                ["default_duration_seconds", "sample_rate_hz", "title"],
            )
            self.assertEqual(analysis_payload["report_output"], str(analysis_report_path))
            self.assertEqual(analysis_payload["report_format"], "yaml")

            changed_states = analysis_payload["changed_state_frequencies"]
            self.assertEqual(changed_states[0]["state"], "alpha")
            self.assertEqual(changed_states[0]["pairs_changed"], 1)
            self.assertEqual(changed_states[0]["pair_indexes"], [0])

            metadata_fields = {entry["field"] for entry in analysis_payload["metadata_field_frequencies"]}
            self.assertEqual(metadata_fields, {"default_duration_seconds", "sample_rate_hz", "title"})
            self.assertEqual(analysis_payload["spatial_change_summary"]["channel_layout_changed_pairs"], 0)

            persisted_analysis = yaml.safe_load(analysis_report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_analysis["pairs_compared"], 2)
            self.assertEqual(persisted_analysis["states_changed_in_all_changed_pairs"], ["alpha"])

    def test_arwif_batch_diff_analyze_tracks_object_spatial_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left.arwif"
            right_path = tmp_dir / "right.arwif"
            diff_report_path = tmp_dir / "object-batch-diff-report.json"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="object",
                            metadata={
                                "duration_seconds": 0.25,
                                "position": {"x": -0.5, "y": 0.0, "z": 0.2},
                                "spread": 0.1,
                                "distance_model": "inverse",
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "listener_anchor": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "title": "Object left",
                    },
                ),
            )

            save_wave_library(
                right_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="object",
                            metadata={
                                "duration_seconds": 0.25,
                                "position": {"x": 0.6, "y": 0.1, "z": 1.0},
                                "orientation": {"x": 0.0, "y": 0.0, "z": 1.0},
                                "spread": 0.4,
                                "distance_model": "linear",
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "listener_anchor": {"x": 0.0, "y": 1.0, "z": 0.0},
                        "title": "Object right",
                    },
                ),
            )

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listener_anchor_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_positioned_state_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_orientation_state_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_states_with_orientation_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_spread_state_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["distance_models_changed_pairs"], 1)

    def test_arwif_batch_review_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_alpha_path = tmp_dir / "left-alpha.arwif"
            right_alpha_path = tmp_dir / "right-alpha.arwif"
            left_beta_path = tmp_dir / "left-beta.arwif"
            right_beta_path = tmp_dir / "right-beta.arwif"
            review_report_path = tmp_dir / "batch-review-report.json"

            save_wave_library(
                left_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
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
                        "title": "Alpha left",
                    },
                ),
            )

            save_wave_library(
                right_alpha_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(392, 0.6)),
                            label="alpha",
                            metadata={"duration_seconds": 0.5},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 0.5,
                        "title": "Alpha right",
                    },
                ),
            )

            save_wave_library(
                left_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            save_wave_library(
                right_beta_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta",
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
                        "title": "Beta pair",
                    },
                ),
            )

            review_payload = self._run_json(
                repo_root,
                "arwif-batch-review",
                "--left",
                str(left_alpha_path),
                str(left_beta_path),
                "--right",
                str(right_alpha_path),
                str(right_beta_path),
                "--output",
                str(review_report_path),
                "--json",
            )

            self.assertTrue(review_payload["is_valid"], review_payload)
            self.assertEqual(review_payload["pairs_compared"], 2)
            self.assertEqual(review_payload["changed_pairs"], 1)
            self.assertEqual(review_payload["unchanged_pairs"], 1)
            self.assertEqual(review_payload["invalid_pairs"], 0)
            self.assertEqual(review_payload["incompatible_pairs"], 0)
            self.assertFalse(review_payload["allow_legacy"])
            self.assertEqual(review_payload["report_output"], str(review_report_path))
            self.assertEqual(review_payload["report_format"], "json")
            self.assertEqual(review_payload["analysis"]["states_changed_in_all_changed_pairs"], ["alpha"])
            self.assertEqual(
                review_payload["analysis"]["metadata_fields_changed_in_all_changed_pairs"],
                ["default_duration_seconds", "sample_rate_hz", "title"],
            )
            self.assertEqual(review_payload["analysis"]["spatial_change_summary"]["channel_layout_changed_pairs"], 0)
            self.assertEqual(len(review_payload["diff_report"]["results"]), 2)

            persisted_review = json.loads(review_report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_review["pairs_compared"], 2)
            self.assertEqual(persisted_review["analysis"]["states_changed_in_all_changed_pairs"], ["alpha"])

    def test_arwif_batch_export_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_artifact_path = tmp_dir / "alpha.arwif"
            second_artifact_path = tmp_dir / "beta.arwif"
            output_dir = tmp_dir / "exports"
            report_path = tmp_dir / "batch-export-report.json"

            save_wave_library(
                first_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8), AtomicWaveUnit(330, 0.7)),
                            label="alpha",
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
                        "title": "Alpha chord",
                    },
                ),
            )

            save_wave_library(
                second_artifact_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(392, 0.6),),
                            label="beta-intro",
                            metadata={"duration_seconds": 0.5},
                        ),
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(523, 0.4),),
                            label="beta-outro",
                            metadata={"duration_seconds": 0.25},
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 12000,
                        "default_duration_seconds": 0.5,
                        "title": "Beta phrase",
                    },
                ),
            )

            batch_payload = self._run_json(
                repo_root,
                "arwif-batch-export",
                str(first_artifact_path),
                str(second_artifact_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(batch_payload["is_valid"], batch_payload)
            self.assertEqual(batch_payload["artifacts_processed"], 2)
            self.assertEqual(batch_payload["exported_count"], 2)
            self.assertEqual(batch_payload["failed_count"], 0)
            self.assertEqual(batch_payload["format"], "yaml")
            self.assertEqual(batch_payload["output_dir"], str(output_dir))
            self.assertEqual(batch_payload["total_state_count"], 3)
            self.assertEqual(batch_payload["total_oscillator_count"], 4)
            self.assertEqual(batch_payload["report_output"], str(report_path))
            self.assertEqual(batch_payload["report_format"], "json")
            self.assertEqual(len(batch_payload["results"]), 2)

            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["artifacts_processed"], 2)
            self.assertEqual(persisted_report["exported_count"], 2)

            expected_outputs = {
                output_dir / "alpha.export.yaml",
                output_dir / "beta.export.yaml",
            }
            for path in expected_outputs:
                self.assertTrue(path.exists(), path)

            alpha_document = yaml.safe_load((output_dir / "alpha.export.yaml").read_text(encoding="utf-8"))
            beta_document = yaml.safe_load((output_dir / "beta.export.yaml").read_text(encoding="utf-8"))
            self.assertEqual(alpha_document["title"], "Alpha chord")
            self.assertEqual(alpha_document["states"][0]["label"], "alpha")
            self.assertEqual(beta_document["title"], "Beta phrase")
            self.assertEqual(len(beta_document["states"]), 2)

            for result in batch_payload["results"]:
                self.assertTrue(result["exported"], result)
                self.assertTrue(result["is_valid"], result)

        def test_arwif_object_spatial_round_trip_cli(self) -> None:
                repo_root = Path(__file__).resolve().parents[1]
                with tempfile.TemporaryDirectory() as tmp_dir_str:
                        tmp_dir = Path(tmp_dir_str)
                        source_spec_path = tmp_dir / "object-spatial.yaml"
                        artifact_path = tmp_dir / "object-spatial.arwif"
                        exported_spec_path = tmp_dir / "object-spatial.export.yaml"
                        roundtrip_artifact_path = tmp_dir / "object-spatial.roundtrip.arwif"

                        source_spec_path.write_text(
                                """
title: Object spatial fixture
listener_anchor:
    x: 0.0
    y: 0.0
    z: 0.0
sample_rate_hz: 12000
default_duration_seconds: 0.5
states:
    - label: near-left
        position:
            x: -0.8
            y: 0.1
            z: 0.2
        orientation:
            x: 0.0
            y: 0.0
            z: 1.0
        spread: 0.2
        distance_model: inverse
        oscillators:
            - hz: 261
                amplitude: 0.8
    - label: far-right
        position:
            x: 0.9
            y: 0.0
            z: 1.6
        spread: 0.5
        distance_model: linear
        oscillators:
            - hz: 392
                amplitude: 0.6
""".strip()
                                + "\n",
                                encoding="utf-8",
                        )

                        spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(source_spec_path), "--json")
                        self.assertTrue(spec_payload["is_valid"], spec_payload)
                        self.assertTrue(spec_payload["stats"]["listener_anchor_present"])
                        self.assertEqual(spec_payload["stats"]["positioned_state_count"], 2)
                        self.assertEqual(spec_payload["stats"]["states_with_orientation"], 1)
                        self.assertEqual(spec_payload["stats"]["states_with_spread"], 2)
                        self.assertEqual(spec_payload["stats"]["distance_models"], ["inverse", "linear"])

                        build_payload = self._run_json(
                                repo_root,
                                "arwif-build",
                                "--spec",
                                str(source_spec_path),
                                "--output",
                                str(artifact_path),
                                "--json",
                        )
                        self.assertTrue(build_payload["is_valid"], build_payload)

                        inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
                        self.assertTrue(inspect_payload["is_valid"], inspect_payload)
                        self.assertEqual(inspect_payload["listener_anchor"]["z"], 0.0)
                        self.assertEqual(inspect_payload["states"][0]["position"]["x"], -0.8)
                        self.assertEqual(inspect_payload["states"][0]["orientation"]["z"], 1.0)
                        self.assertEqual(inspect_payload["states"][1]["spread"], 0.5)
                        self.assertEqual(inspect_payload["states"][1]["distance_model"], "linear")
                        self.assertEqual(inspect_payload["spatial_summary"]["positioned_states"], 2)
                        self.assertEqual(inspect_payload["spatial_summary"]["states_with_orientation"], 1)
                        self.assertEqual(inspect_payload["spatial_summary"]["states_with_spread"], 2)
                        self.assertEqual(inspect_payload["spatial_summary"]["distance_models"], ["inverse", "linear"])

                        export_payload = self._run_json(
                                repo_root,
                                "arwif-export",
                                str(artifact_path),
                                str(exported_spec_path),
                                "--json",
                        )
                        self.assertTrue(export_payload["is_valid"], export_payload)

                        exported_document = yaml.safe_load(exported_spec_path.read_text(encoding="utf-8"))
                        self.assertEqual(exported_document["listener_anchor"]["x"], 0.0)
                        self.assertEqual(exported_document["states"][0]["position"]["y"], 0.1)
                        self.assertEqual(exported_document["states"][0]["orientation"]["z"], 1.0)
                        self.assertEqual(exported_document["states"][1]["spread"], 0.5)
                        self.assertEqual(exported_document["states"][1]["distance_model"], "linear")

                        import_payload = self._run_json(
                                repo_root,
                                "arwif-import",
                                "--spec",
                                str(exported_spec_path),
                                "--output",
                                str(roundtrip_artifact_path),
                                "--json",
                        )
                        self.assertTrue(import_payload["is_valid"], import_payload)

                        diff_payload = self._run_json(
                                repo_root,
                                "arwif-diff",
                                str(artifact_path),
                                str(roundtrip_artifact_path),
                                "--json",
                        )
                        self.assertEqual(diff_payload["change_summary"]["metadata_fields_changed"], 0)
                        self.assertEqual(diff_payload["change_summary"]["changed_states"], 0)
                        self.assertFalse(diff_payload["spatial_changes"]["listener_anchor_changed"])
                        self.assertFalse(diff_payload["spatial_changes"]["distance_models_changed"])

        def test_arwif_validate_spec_rejects_invalid_object_spatial_fields(self) -> None:
                repo_root = Path(__file__).resolve().parents[1]
                with tempfile.TemporaryDirectory() as tmp_dir_str:
                        tmp_dir = Path(tmp_dir_str)
                        spec_path = tmp_dir / "invalid-object-spatial.yaml"
                        spec_path.write_text(
                                """
title: Invalid object spatial
listener_anchor:
    x: 0.0
    y: nope
    z: 0.0
sample_rate_hz: 8000
default_duration_seconds: 0.25
states:
    - label: broken
        position:
            x: left
            y: 0.0
            z: 0.0
        orientation:
            x: 0.0
            y: 0.0
        spread: -0.1
        distance_model: weird
        oscillators:
            - hz: 261
                amplitude: 0.8
""".strip()
                                + "\n",
                                encoding="utf-8",
                        )

                        spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(spec_path), "--json", allow_failure=True)
                        self.assertFalse(spec_payload["is_valid"])
                        self.assertIn("listener_anchor.y must be a finite number", spec_payload["errors"])
                        self.assertIn("states[0].position.x must be a finite number", spec_payload["errors"])
                        self.assertIn("states[0].orientation.z must be a finite number", spec_payload["errors"])
                        self.assertIn("states[0].spread must be non-negative", spec_payload["errors"])
                        self.assertIn(
                                "states[0].distance_model must be one of: none, inverse, linear, exponential",
                                spec_payload["errors"],
                        )

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


class ARWIFObjectSpatialIntegrationTest(unittest.TestCase):
    def test_arwif_object_spatial_round_trip_cli(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            source_spec_path = tmp_dir / "object-spatial.yaml"
            artifact_path = tmp_dir / "object-spatial.arwif"
            exported_spec_path = tmp_dir / "object-spatial.export.yaml"
            roundtrip_artifact_path = tmp_dir / "object-spatial.roundtrip.arwif"

            source_spec_path.write_text(
                "\n".join(
                    [
                        "title: Object spatial fixture",
                        "reference_frame: scene",
                        "listener_anchor:",
                        "  x: 0.0",
                        "  y: 0.0",
                        "  z: 0.0",
                        "sample_rate_hz: 12000",
                        "default_duration_seconds: 0.5",
                        "states:",
                        "  - label: near-left",
                        "    source_id: bell.near-left",
                        "    source_groups:",
                        "      - percussion",
                        "      - foreground",
                        "    position:",
                        "      x: -0.8",
                        "      y: 0.1",
                        "      z: 0.2",
                        "    orientation:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "    spread: 0.2",
                        "    distance_model: inverse",
                        "    oscillators:",
                        "      - hz: 261",
                        "        amplitude: 0.8",
                        "  - label: far-right",
                        "    source_id: synth.far-right",
                        "    source_groups:",
                        "      - pads",
                        "      - background",
                        "    position:",
                        "      x: 0.9",
                        "      y: 0.0",
                        "      z: 1.6",
                        "    spread: 0.5",
                        "    distance_model: linear",
                        "    oscillators:",
                        "      - hz: 392",
                        "        amplitude: 0.6",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(source_spec_path), "--json")
            self.assertTrue(spec_payload["is_valid"], spec_payload)
            self.assertEqual(spec_payload["stats"]["reference_frame"], "scene")
            self.assertTrue(spec_payload["stats"]["listener_anchor_present"])
            self.assertEqual(spec_payload["stats"]["positioned_state_count"], 2)
            self.assertEqual(spec_payload["stats"]["states_with_orientation"], 1)
            self.assertEqual(spec_payload["stats"]["states_with_spread"], 2)
            self.assertEqual(spec_payload["stats"]["states_with_source_id"], 2)
            self.assertEqual(spec_payload["stats"]["source_groups"], ["background", "foreground", "pads", "percussion"])
            self.assertEqual(spec_payload["stats"]["distance_models"], ["inverse", "linear"])

            build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(source_spec_path),
                "--output",
                str(artifact_path),
                "--json",
            )
            self.assertTrue(build_payload["is_valid"], build_payload)

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
            self.assertTrue(inspect_payload["is_valid"], inspect_payload)
            self.assertEqual(inspect_payload["reference_frame"], "scene")
            self.assertEqual(inspect_payload["listener_anchor"]["z"], 0.0)
            self.assertEqual(inspect_payload["states"][0]["source_id"], "bell.near-left")
            self.assertEqual(inspect_payload["states"][0]["source_groups"], ["percussion", "foreground"])
            self.assertEqual(inspect_payload["states"][0]["position"]["x"], -0.8)
            self.assertEqual(inspect_payload["states"][0]["orientation"]["z"], 1.0)
            self.assertEqual(inspect_payload["states"][1]["spread"], 0.5)
            self.assertEqual(inspect_payload["states"][1]["distance_model"], "linear")
            self.assertEqual(inspect_payload["spatial_summary"]["reference_frame"], "scene")
            self.assertEqual(inspect_payload["spatial_summary"]["positioned_states"], 2)
            self.assertEqual(inspect_payload["spatial_summary"]["states_with_orientation"], 1)
            self.assertEqual(inspect_payload["spatial_summary"]["states_with_spread"], 2)
            self.assertEqual(inspect_payload["spatial_summary"]["states_with_source_id"], 2)
            self.assertEqual(
                inspect_payload["spatial_summary"]["source_groups"],
                ["background", "foreground", "pads", "percussion"],
            )
            self.assertEqual(inspect_payload["spatial_summary"]["distance_models"], ["inverse", "linear"])

            export_payload = self._run_json(
                repo_root,
                "arwif-export",
                str(artifact_path),
                str(exported_spec_path),
                "--json",
            )
            self.assertTrue(export_payload["is_valid"], export_payload)

            exported_document = yaml.safe_load(exported_spec_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_document["reference_frame"], "scene")
            self.assertEqual(exported_document["listener_anchor"]["x"], 0.0)
            self.assertEqual(exported_document["states"][0]["source_id"], "bell.near-left")
            self.assertEqual(exported_document["states"][1]["source_groups"], ["pads", "background"])
            self.assertEqual(exported_document["states"][0]["position"]["y"], 0.1)
            self.assertEqual(exported_document["states"][0]["orientation"]["z"], 1.0)
            self.assertEqual(exported_document["states"][1]["spread"], 0.5)
            self.assertEqual(exported_document["states"][1]["distance_model"], "linear")

            import_payload = self._run_json(
                repo_root,
                "arwif-import",
                "--spec",
                str(exported_spec_path),
                "--output",
                str(roundtrip_artifact_path),
                "--json",
            )
            self.assertTrue(import_payload["is_valid"], import_payload)

            diff_payload = self._run_json(
                repo_root,
                "arwif-diff",
                str(artifact_path),
                str(roundtrip_artifact_path),
                "--json",
            )
            self.assertEqual(diff_payload["change_summary"]["metadata_fields_changed"], 0)
            self.assertEqual(diff_payload["change_summary"]["changed_states"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["listener_anchor_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["reference_frame_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["source_groups_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["distance_models_changed"])

    def test_arwif_trajectory_round_trip_cli(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            source_spec_path = tmp_dir / "trajectory.yaml"
            artifact_path = tmp_dir / "trajectory.arwif"
            exported_spec_path = tmp_dir / "trajectory.export.yaml"
            roundtrip_artifact_path = tmp_dir / "trajectory.roundtrip.arwif"

            source_spec_path.write_text(
                "\n".join(
                    [
                        "title: Trajectory fixture",
                        "listener_anchor:",
                        "  x: 0.0",
                        "  y: 0.0",
                        "  z: 0.0",
                        "sample_rate_hz: 12000",
                        "default_duration_seconds: 0.5",
                        "states:",
                        "  - label: moving-source",
                        "    duration_seconds: 0.5",
                        "    position:",
                        "      x: -0.8",
                        "      y: 0.0",
                        "      z: 0.2",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: -0.8",
                        "          y: 0.0",
                        "          z: 0.2",
                        "      - offset_seconds: 0.25",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.1",
                        "          z: 0.8",
                        "      - offset_seconds: 0.5",
                        "        position:",
                        "          x: 0.7",
                        "          y: 0.0",
                        "          z: 1.1",
                        "    orientation:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "    spread: 0.2",
                        "    distance_model: inverse",
                        "    oscillators:",
                        "      - hz: 261",
                        "        amplitude: 0.8",
                        "  - label: static-source",
                        "    position:",
                        "      x: 0.8",
                        "      y: 0.0",
                        "      z: 1.6",
                        "    oscillators:",
                        "      - hz: 392",
                        "        amplitude: 0.6",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(source_spec_path), "--json")
            self.assertTrue(spec_payload["is_valid"], spec_payload)
            self.assertEqual(spec_payload["stats"]["states_with_trajectory"], 1)
            self.assertEqual(spec_payload["stats"]["trajectory_point_count"], 3)

            build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(source_spec_path),
                "--output",
                str(artifact_path),
                "--json",
            )
            self.assertTrue(build_payload["is_valid"], build_payload)

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
            self.assertTrue(inspect_payload["is_valid"], inspect_payload)
            self.assertEqual(len(inspect_payload["states"][0]["trajectory"]), 3)
            self.assertEqual(inspect_payload["states"][0]["trajectory"][1]["position"]["z"], 0.8)
            self.assertEqual(inspect_payload["spatial_summary"]["states_with_trajectory"], 1)
            self.assertEqual(inspect_payload["spatial_summary"]["trajectory_point_count"], 3)

            export_payload = self._run_json(
                repo_root,
                "arwif-export",
                str(artifact_path),
                str(exported_spec_path),
                "--json",
            )
            self.assertTrue(export_payload["is_valid"], export_payload)

            exported_document = yaml.safe_load(exported_spec_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_document["states"][0]["trajectory"][2]["offset_seconds"], 0.5)
            self.assertEqual(exported_document["states"][0]["trajectory"][2]["position"]["x"], 0.7)

            import_payload = self._run_json(
                repo_root,
                "arwif-import",
                "--spec",
                str(exported_spec_path),
                "--output",
                str(roundtrip_artifact_path),
                "--json",
            )
            self.assertTrue(import_payload["is_valid"], import_payload)

            diff_payload = self._run_json(
                repo_root,
                "arwif-diff",
                str(artifact_path),
                str(roundtrip_artifact_path),
                "--json",
            )
            self.assertEqual(diff_payload["change_summary"]["changed_states"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["trajectories_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["trajectory_point_count_delta"], 0)

    def test_arwif_validate_spec_rejects_invalid_trajectory_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid-trajectory.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "title: Invalid trajectory",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "states:",
                        "  - label: broken-motion",
                        "    duration_seconds: 0.25",
                        "    trajectory:",
                        "      - offset_seconds: 0.2",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 0.1",
                        "        position:",
                        "          x: 1.0",
                        "          y: bad",
                        "          z: 0.0",
                        "      - offset_seconds: 0.3",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "    oscillators:",
                        "      - hz: 261",
                        "        amplitude: 0.8",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(spec_path), "--json", allow_failure=True)
            self.assertFalse(spec_payload["is_valid"])
            self.assertIn(
                "states[0].trajectory must be sorted by non-decreasing offset_seconds",
                spec_payload["errors"],
            )
            self.assertIn(
                "states[0].trajectory[1].position.y must be a finite number",
                spec_payload["errors"],
            )
            self.assertIn(
                "states[0].trajectory[2].offset_seconds must not exceed state duration 0.25",
                spec_payload["errors"],
            )

    def test_arwif_batch_diff_analyze_tracks_trajectory_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-trajectory.arwif"
            right_path = tmp_dir / "right-trajectory.arwif"
            diff_report_path = tmp_dir / "trajectory-batch-diff-report.json"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="moving-object",
                            metadata={
                                "duration_seconds": 0.25,
                                "trajectory": [
                                    {
                                        "offset_seconds": 0.0,
                                        "position": {"x": -0.5, "y": 0.0, "z": 0.2},
                                    },
                                    {
                                        "offset_seconds": 0.25,
                                        "position": {"x": 0.0, "y": 0.0, "z": 0.8},
                                    },
                                ],
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "title": "Trajectory left",
                    },
                ),
            )

            save_wave_library(
                right_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="moving-object",
                            metadata={
                                "duration_seconds": 0.25,
                                "trajectory": [
                                    {
                                        "offset_seconds": 0.0,
                                        "position": {"x": -0.5, "y": 0.0, "z": 0.2},
                                    },
                                    {
                                        "offset_seconds": 0.125,
                                        "position": {"x": 0.3, "y": 0.0, "z": 0.6},
                                    },
                                    {
                                        "offset_seconds": 0.25,
                                        "position": {"x": 0.8, "y": 0.0, "z": 1.1},
                                    },
                                ],
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "title": "Trajectory right",
                    },
                ),
            )

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["trajectory_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_trajectory_state_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_trajectory_point_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_trajectory_point_delta"], 1)

    def test_arwif_validate_spec_rejects_invalid_object_spatial_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid-object-spatial.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "title: Invalid object spatial",
                        "reference_frame: galaxy",
                        "listener_anchor:",
                        "  x: 0.0",
                        "  y: nope",
                        "  z: 0.0",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "states:",
                        "  - label: broken",
                        "    source_id: 12",
                        "    source_groups:",
                        "      - ok",
                        "      - ''",
                        "    position:",
                        "      x: left",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    orientation:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "    spread: -0.1",
                        "    distance_model: weird",
                        "    oscillators:",
                        "      - hz: 261",
                        "        amplitude: 0.8",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(spec_path), "--json", allow_failure=True)
            self.assertFalse(spec_payload["is_valid"])
            self.assertIn("reference_frame must be one of: listener, scene, world", spec_payload["errors"])
            self.assertIn("listener_anchor.y must be a finite number", spec_payload["errors"])
            self.assertIn("states[0].source_id must be a string", spec_payload["errors"])
            self.assertIn("states[0].source_groups[1] must be a non-empty string", spec_payload["errors"])
            self.assertIn("states[0].position.x must be a finite number", spec_payload["errors"])
            self.assertIn("states[0].orientation.z must be a finite number", spec_payload["errors"])
            self.assertIn("states[0].spread must be non-negative", spec_payload["errors"])
            self.assertIn(
                "states[0].distance_model must be one of: none, inverse, linear, exponential",
                spec_payload["errors"],
            )

    def test_arwif_batch_diff_analyze_tracks_identity_bridge_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-identity.arwif"
            right_path = tmp_dir / "right-identity.arwif"
            diff_report_path = tmp_dir / "identity-batch-diff-report.json"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="moving-object",
                            metadata={
                                "duration_seconds": 0.25,
                                "source_id": "object.alpha",
                                "source_groups": ["foreground"],
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "reference_frame": "listener",
                        "title": "Identity left",
                    },
                ),
            )

            save_wave_library(
                right_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="moving-object",
                            metadata={
                                "duration_seconds": 0.25,
                                "source_id": "object.alpha.v2",
                                "source_groups": ["foreground", "harmonics"],
                            },
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "reference_frame": "scene",
                        "title": "Identity right",
                    },
                ),
            )

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reference_frame_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_source_id_state_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_states_with_source_id_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["source_groups_changed_pairs"], 1)

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
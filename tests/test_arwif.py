from __future__ import annotations

import json
import math
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
    def test_shipped_room_review_examples_validate_and_batch_review(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline_spec_path = repo_root / "examples" / "arwif" / "ROOM_REVIEW_baseline_v0_1.yaml"
        candidate_spec_path = repo_root / "examples" / "arwif" / "ROOM_REVIEW_candidate_v0_1.yaml"

        self.assertTrue(baseline_spec_path.exists())
        self.assertTrue(candidate_spec_path.exists())

        baseline_spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(baseline_spec_path), "--json")
        candidate_spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(candidate_spec_path), "--json")
        self.assertTrue(baseline_spec_payload["is_valid"], baseline_spec_payload)
        self.assertTrue(candidate_spec_payload["is_valid"], candidate_spec_payload)

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            baseline_artifact_path = tmp_dir / "ROOM_REVIEW_baseline_v0_1.arwif"
            candidate_artifact_path = tmp_dir / "ROOM_REVIEW_candidate_v0_1.arwif"
            review_report_path = tmp_dir / "ROOM_REVIEW_batch_review.json"

            baseline_build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(baseline_spec_path),
                "--output",
                str(baseline_artifact_path),
                "--json",
            )
            candidate_build_payload = self._run_json(
                repo_root,
                "arwif-build",
                "--spec",
                str(candidate_spec_path),
                "--output",
                str(candidate_artifact_path),
                "--json",
            )
            self.assertTrue(baseline_build_payload["is_valid"], baseline_build_payload)
            self.assertTrue(candidate_build_payload["is_valid"], candidate_build_payload)

            review_payload = self._run_json(
                repo_root,
                "arwif-batch-review",
                "--left",
                str(baseline_artifact_path),
                "--right",
                str(candidate_artifact_path),
                "--output",
                str(review_report_path),
                "--json",
            )
            self.assertTrue(review_payload["is_valid"], review_payload)
            self.assertTrue(review_report_path.exists())
            analysis_payload = review_payload["analysis"]
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_id_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_class_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["surface_treatment_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_absorption_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_diffusion_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reflection_policy_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["renderer_adaptation_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zones_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zone_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_intents_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_intents_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_roles_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_coverage_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_coverage_intents_count_delta"], 0)

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
            self.assertEqual(diff_payload["max_frequency_hz_delta"], 193)
            self.assertIn("channel_gains", diff_payload["state_changes"]["CE"]["metadata_changes"])
            self.assertEqual(
                diff_payload["state_changes"]["CE"]["metadata_changes"]["channel_gains"]["right"]["R"],
                1.0,
            )
            self.assertEqual(diff_payload["left_spatial_summary"]["channel_layout"], "stereo")
            self.assertEqual(diff_payload["right_spatial_summary"]["active_channels"], ["L", "R"])
            self.assertFalse(diff_payload["spatial_changes"]["active_channels_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["active_channels_count_delta"], 0)
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

    def test_arwif_inspect_exposes_metadata_and_realm_references(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "realm-links.yaml"
            artifact_path = tmp_dir / "realm-links.arwif"

            spec_path.write_text(
                """
title: Realm-linked motif
sample_rate_hz: 8000
default_duration_seconds: 0.25
metadata:
  motif_family: ambient
  related_realms:
    - realm: rwif
      role: semantic_memory
      artifact: memory/demo.rwif
    - realm: vrwif
      role: scene
      spec: scenes/demo.yaml
states:
  - label: intro
    oscillators:
      - hz: 261
        amplitude: 0.8
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
            self.assertTrue(build_payload["is_valid"], build_payload)

            inspect_payload = self._run_json(repo_root, "arwif-inspect", str(artifact_path), "--json")
            self.assertTrue(inspect_payload["is_valid"], inspect_payload)
            self.assertEqual(inspect_payload["metadata"]["motif_family"], "ambient")
            self.assertEqual(len(inspect_payload["realm_references"]), 2)
            self.assertEqual(inspect_payload["realm_references"][0]["realm"], "rwif")
            self.assertEqual(inspect_payload["realm_references"][1]["realm"], "vrwif")
            self.assertEqual(inspect_payload["realm_references"][0]["artifact"], "memory/demo.rwif")

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
            self.assertEqual(analysis_payload["spatial_change_summary"]["active_channels_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_active_channels_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_active_channels_count_delta"], 0)

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

    def test_arwif_room_aware_round_trip_cli(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            source_spec_path = tmp_dir / "room-aware.yaml"
            artifact_path = tmp_dir / "room-aware.arwif"
            exported_spec_path = tmp_dir / "room-aware.export.yaml"
            roundtrip_artifact_path = tmp_dir / "room-aware.roundtrip.arwif"

            source_spec_path.write_text(
                "\n".join(
                    [
                        "title: Room aware fixture",
                        "channel_layout: stereo",
                        "reference_frame: scene",
                        "listener_anchor:",
                        "  x: 0.0",
                        "  y: 1.2",
                        "  z: 0.0",
                        "room:",
                        "  dimensions:",
                        "    width_m: 10.0",
                        "    depth_m: 14.0",
                        "    height_m: 4.5",
                        "  geometry_reference:",
                        "    geometry_id: studio.a",
                        "    geometry_class: shoebox",
                        "  surface_profile: reflective",
                        "  surface_treatment:",
                        "    absorption: low",
                        "    diffusion: balanced",
                        "  reflection_policy:",
                        "    style: balanced",
                        "    early_reflections: natural",
                        "    late_reverb: controlled",
                        "  renderer_adaptation_hints:",
                        "    target_playback: multichannel_room",
                        "    spatial_priority: envelopment",
                        "    downmix_policy: preserve_positions",
                        "  listening_zones:",
                        "    - zone_id: sweet-spot",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 1.2",
                        "        z: 0.0",
                        "      radius_m: 1.5",
                        "      intent: focused",
                        "    - zone_id: rear-fill",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 1.2",
                        "        z: 3.5",
                        "      radius_m: 2.0",
                        "      intent: diffuse",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "sample_rate_hz: 12000",
                        "default_duration_seconds: 0.5",
                        "states:",
                        "  - label: near-source",
                        "    source_id: bell.near",
                        "    source_groups:",
                        "      - foreground",
                        "    position:",
                        "      x: -0.6",
                        "      y: 1.3",
                        "      z: 1.0",
                        "    oscillators:",
                        "      - hz: 261",
                        "        amplitude: 0.8",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            spec_payload = self._run_json(repo_root, "arwif-validate-spec", str(source_spec_path), "--json")
            self.assertTrue(spec_payload["is_valid"], spec_payload)
            self.assertTrue(spec_payload["stats"]["room_present"])
            self.assertTrue(spec_payload["stats"]["room_dimensions_present"])
            self.assertTrue(spec_payload["stats"]["geometry_reference_present"])
            self.assertEqual(spec_payload["stats"]["room_geometry_id"], "studio.a")
            self.assertEqual(spec_payload["stats"]["room_geometry_class"], "shoebox")
            self.assertEqual(spec_payload["stats"]["room_surface_profile"], "reflective")
            self.assertTrue(spec_payload["stats"]["surface_treatment_present"])
            self.assertEqual(spec_payload["stats"]["room_surface_absorption"], "low")
            self.assertEqual(spec_payload["stats"]["room_surface_diffusion"], "balanced")
            self.assertTrue(spec_payload["stats"]["reflection_policy_present"])
            self.assertEqual(spec_payload["stats"]["room_reflection_style"], "balanced")
            self.assertEqual(spec_payload["stats"]["room_early_reflections"], "natural")
            self.assertEqual(spec_payload["stats"]["room_late_reverb"], "controlled")
            self.assertTrue(spec_payload["stats"]["renderer_adaptation_present"])
            self.assertEqual(spec_payload["stats"]["room_target_playback"], "multichannel_room")
            self.assertEqual(spec_payload["stats"]["room_spatial_priority"], "envelopment")
            self.assertEqual(spec_payload["stats"]["room_downmix_policy"], "preserve_positions")
            self.assertEqual(spec_payload["stats"]["listening_zone_count"], 2)
            self.assertEqual(spec_payload["stats"]["listening_zone_ids"], ["rear-fill", "sweet-spot"])
            self.assertEqual(spec_payload["stats"]["listening_zone_intents"], ["diffuse", "focused"])
            self.assertEqual(spec_payload["stats"]["speaker_count"], 2)
            self.assertEqual(spec_payload["stats"]["speaker_ids"], ["left-main", "right-main"])
            self.assertEqual(spec_payload["stats"]["speaker_channels"], ["L", "R"])
            self.assertEqual(spec_payload["stats"]["speaker_roles"], ["main"])
            self.assertEqual(spec_payload["stats"]["speaker_coverage_intents"], ["focused"])

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
            self.assertEqual(inspect_payload["room"]["geometry_reference"]["geometry_id"], "studio.a")
            self.assertEqual(inspect_payload["room"]["geometry_reference"]["geometry_class"], "shoebox")
            self.assertEqual(inspect_payload["room"]["surface_profile"], "reflective")
            self.assertEqual(inspect_payload["room"]["surface_treatment"]["absorption"], "low")
            self.assertEqual(inspect_payload["room"]["surface_treatment"]["diffusion"], "balanced")
            self.assertEqual(inspect_payload["room"]["reflection_policy"]["style"], "balanced")
            self.assertEqual(inspect_payload["room"]["renderer_adaptation_hints"]["target_playback"], "multichannel_room")
            self.assertEqual(inspect_payload["room"]["dimensions"]["height_m"], 4.5)
            self.assertEqual(inspect_payload["room"]["listening_zones"][0]["zone_id"], "sweet-spot")
            self.assertEqual(inspect_payload["room"]["speakers"][0]["speaker_id"], "left-main")
            self.assertEqual(inspect_payload["room"]["speakers"][1]["channel"], "R")
            self.assertEqual(inspect_payload["room"]["speakers"][0]["role"], "main")
            self.assertEqual(inspect_payload["room"]["speakers"][0]["coverage_intent"], "focused")
            self.assertTrue(inspect_payload["spatial_summary"]["room_present"])
            self.assertTrue(inspect_payload["spatial_summary"]["geometry_reference_present"])
            self.assertEqual(inspect_payload["spatial_summary"]["room_geometry_id"], "studio.a")
            self.assertEqual(inspect_payload["spatial_summary"]["room_geometry_class"], "shoebox")
            self.assertEqual(inspect_payload["spatial_summary"]["room_surface_profile"], "reflective")
            self.assertTrue(inspect_payload["spatial_summary"]["surface_treatment_present"])
            self.assertEqual(inspect_payload["spatial_summary"]["room_surface_absorption"], "low")
            self.assertEqual(inspect_payload["spatial_summary"]["room_surface_diffusion"], "balanced")
            self.assertTrue(inspect_payload["spatial_summary"]["reflection_policy_present"])
            self.assertEqual(inspect_payload["spatial_summary"]["room_reflection_style"], "balanced")
            self.assertEqual(inspect_payload["spatial_summary"]["room_early_reflections"], "natural")
            self.assertEqual(inspect_payload["spatial_summary"]["room_late_reverb"], "controlled")
            self.assertTrue(inspect_payload["spatial_summary"]["renderer_adaptation_present"])
            self.assertEqual(inspect_payload["spatial_summary"]["room_target_playback"], "multichannel_room")
            self.assertEqual(inspect_payload["spatial_summary"]["room_spatial_priority"], "envelopment")
            self.assertEqual(inspect_payload["spatial_summary"]["room_downmix_policy"], "preserve_positions")
            self.assertEqual(inspect_payload["spatial_summary"]["listening_zone_count"], 2)
            self.assertEqual(inspect_payload["spatial_summary"]["listening_zone_ids"], ["sweet-spot", "rear-fill"])
            self.assertEqual(inspect_payload["spatial_summary"]["listening_zone_intents"], ["diffuse", "focused"])
            self.assertEqual(inspect_payload["spatial_summary"]["speaker_count"], 2)
            self.assertEqual(inspect_payload["spatial_summary"]["speaker_ids"], ["left-main", "right-main"])
            self.assertEqual(inspect_payload["spatial_summary"]["speaker_channels"], ["L", "R"])
            self.assertEqual(inspect_payload["spatial_summary"]["speaker_roles"], ["main"])
            self.assertEqual(inspect_payload["spatial_summary"]["speaker_coverage_intents"], ["focused"])

            export_payload = self._run_json(
                repo_root,
                "arwif-export",
                str(artifact_path),
                str(exported_spec_path),
                "--json",
            )
            self.assertTrue(export_payload["is_valid"], export_payload)

            exported_document = yaml.safe_load(exported_spec_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_document["room"]["dimensions"]["width_m"], 10.0)
            self.assertEqual(exported_document["room"]["geometry_reference"]["geometry_id"], "studio.a")
            self.assertEqual(exported_document["room"]["geometry_reference"]["geometry_class"], "shoebox")
            self.assertEqual(exported_document["room"]["surface_profile"], "reflective")
            self.assertEqual(exported_document["room"]["surface_treatment"]["absorption"], "low")
            self.assertEqual(exported_document["room"]["surface_treatment"]["diffusion"], "balanced")
            self.assertEqual(exported_document["room"]["reflection_policy"]["late_reverb"], "controlled")
            self.assertEqual(exported_document["room"]["renderer_adaptation_hints"]["downmix_policy"], "preserve_positions")
            self.assertEqual(exported_document["room"]["listening_zones"][1]["zone_id"], "rear-fill")
            self.assertEqual(exported_document["room"]["speakers"][0]["speaker_id"], "left-main")
            self.assertEqual(exported_document["room"]["speakers"][1]["channel"], "R")
            self.assertEqual(exported_document["room"]["speakers"][0]["role"], "main")
            self.assertEqual(exported_document["room"]["speakers"][0]["coverage_intent"], "focused")

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
            self.assertFalse(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_dimensions_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["geometry_reference_present_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["geometry_reference_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_geometry_id_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_geometry_class_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_surface_profile_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["surface_treatment_present_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["surface_treatment_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_surface_absorption_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_surface_diffusion_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["reflection_policy_present_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["reflection_policy_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_reflection_style_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_early_reflections_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_late_reverb_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["renderer_adaptation_present_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["renderer_adaptation_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_target_playback_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_spatial_priority_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["room_downmix_policy_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["listening_zones_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["listening_zone_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_intents_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_ids_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_ids_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_ids_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["speaker_channels_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_channels_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_roles_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_roles_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_coverage_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["speaker_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["source_groups_count_delta"], 0)

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

    def test_arwif_validate_spec_rejects_invalid_room_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid-room.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "title: Invalid room fixture",
                        "channel_layout: stereo",
                        "room:",
                        "  dimensions:",
                        "    width_m: -4.0",
                        "    depth_m: nope",
                        "    height_m: 0.0",
                        "  geometry_reference:",
                        "    geometry_id: ''",
                        "    geometry_class: geodesic",
                        "  surface_profile: cathedral",
                        "  surface_treatment:",
                        "    absorption: extreme",
                        "    diffusion: chaotic",
                        "  reflection_policy:",
                        "    style: huge",
                        "    early_reflections: metallic",
                        "    late_reverb: endless",
                        "  renderer_adaptation_hints:",
                        "    target_playback: cinema-dome",
                        "    spatial_priority: gigantic",
                        "    downmix_policy: preserve_everything",
                        "  listening_zones:",
                        "    - zone_id: ''",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: nope",
                        "        z: 0.0",
                        "      radius_m: 0.0",
                        "      intent: everywhere",
                        "  speakers:",
                        "    - speaker_id: ''",
                        "      anchor:",
                        "        x: left",
                        "        y: 1.0",
                        "        z: 0.0",
                        "      channel: C",
                        "      role: sidefill",
                        "      coverage_intent: everywhere",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "states:",
                        "  - label: tone",
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
            self.assertIn("room.dimensions.width_m must be a positive finite number", spec_payload["errors"])
            self.assertIn("room.dimensions.depth_m must be a positive finite number", spec_payload["errors"])
            self.assertIn("room.dimensions.height_m must be a positive finite number", spec_payload["errors"])
            self.assertIn("room.geometry_reference.geometry_id must be a non-empty string", spec_payload["errors"])
            self.assertIn(
                "room.geometry_reference.geometry_class must be one of: shoebox, fan, arena, corridor, irregular",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.surface_profile must be one of: dry, damped, neutral, reflective, diffuse",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.surface_treatment.absorption must be one of: low, balanced, high",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.surface_treatment.diffusion must be one of: focused, balanced, scattered",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.reflection_policy.style must be one of: direct, balanced, enveloping",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.reflection_policy.early_reflections must be one of: reduced, natural, emphasized",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.reflection_policy.late_reverb must be one of: dry, controlled, lush",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.speakers[0].role must be one of: main, surround, height, fill",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.renderer_adaptation_hints.target_playback must be one of: headphones, stereo_speakers, multichannel_room, portable_device",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.renderer_adaptation_hints.spatial_priority must be one of: precision, balanced, envelopment",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.renderer_adaptation_hints.downmix_policy must be one of: preserve_positions, preserve_focus, preserve_energy",
                spec_payload["errors"],
            )
            self.assertIn("room.listening_zones[0].zone_id must be a non-empty string", spec_payload["errors"])
            self.assertIn("room.listening_zones[0].anchor.y must be a finite number", spec_payload["errors"])
            self.assertIn("room.listening_zones[0].radius_m must be a positive finite number", spec_payload["errors"])
            self.assertIn(
                "room.listening_zones[0].intent must be one of: focused, balanced, diffuse, casual",
                spec_payload["errors"],
            )
            self.assertIn("room.speakers[0].speaker_id must be a non-empty string", spec_payload["errors"])
            self.assertIn("room.speakers[0].anchor.x must be a finite number", spec_payload["errors"])
            self.assertIn("room.speakers[0].channel must be one of: L, R", spec_payload["errors"])
            self.assertIn(
                "room.speakers[0].role must be one of: main, surround, height, fill",
                spec_payload["errors"],
            )
            self.assertIn(
                "room.speakers[0].coverage_intent must be one of: focused, balanced, wide, ambient",
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

    def test_arwif_batch_diff_analyze_tracks_room_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-room.arwif"
            right_path = tmp_dir / "right-room.arwif"
            diff_report_path = tmp_dir / "room-batch-diff-report.json"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(261, 0.8),),
                            label="room-tone",
                            metadata={"duration_seconds": 0.25},
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
                        "title": "Room left",
                        "room": {
                            "dimensions": {"width_m": 8.0, "depth_m": 10.0, "height_m": 3.5},
                            "geometry_reference": {
                                "geometry_id": "left-room",
                                "geometry_class": "corridor",
                            },
                            "surface_profile": "dry",
                            "surface_treatment": {
                                "absorption": "high",
                                "diffusion": "focused",
                            },
                            "reflection_policy": {
                                "style": "direct",
                                "early_reflections": "reduced",
                                "late_reverb": "dry",
                            },
                            "renderer_adaptation_hints": {
                                "target_playback": "headphones",
                                "spatial_priority": "precision",
                                "downmix_policy": "preserve_focus",
                            },
                            "speakers": [
                                {
                                    "speaker_id": "left-main",
                                    "anchor": {"x": -2.0, "y": 1.2, "z": 2.0},
                                    "channel": "L",
                                    "role": "main",
                                    "coverage_intent": "focused",
                                }
                            ],
                            "listening_zones": [
                                {
                                    "zone_id": "sweet-spot",
                                    "anchor": {"x": 0.0, "y": 1.2, "z": 0.0},
                                    "radius_m": 1.5,
                                    "intent": "focused",
                                }
                            ],
                        },
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
                            label="room-tone",
                            metadata={"duration_seconds": 0.25},
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
                        "title": "Room right",
                        "room": {
                            "dimensions": {"width_m": 12.0, "depth_m": 15.0, "height_m": 5.0},
                            "geometry_reference": {
                                "geometry_id": "right-room",
                                "geometry_class": "arena",
                            },
                            "surface_profile": "reflective",
                            "surface_treatment": {
                                "absorption": "low",
                                "diffusion": "scattered",
                            },
                            "reflection_policy": {
                                "style": "enveloping",
                                "early_reflections": "emphasized",
                                "late_reverb": "lush",
                            },
                            "renderer_adaptation_hints": {
                                "target_playback": "multichannel_room",
                                "spatial_priority": "envelopment",
                                "downmix_policy": "preserve_positions",
                            },
                            "speakers": [
                                {
                                    "speaker_id": "left-main",
                                    "anchor": {"x": -2.5, "y": 1.2, "z": 2.5},
                                    "channel": "L",
                                    "role": "main",
                                    "coverage_intent": "wide",
                                },
                                {
                                    "speaker_id": "right-main",
                                    "anchor": {"x": 2.5, "y": 1.2, "z": 2.5},
                                    "channel": "R",
                                    "role": "surround",
                                    "coverage_intent": "wide",
                                },
                            ],
                            "listening_zones": [
                                {
                                    "zone_id": "sweet-spot",
                                    "anchor": {"x": 0.0, "y": 1.2, "z": 0.0},
                                    "radius_m": 1.5,
                                    "intent": "focused",
                                },
                                {
                                    "zone_id": "rear-fill",
                                    "anchor": {"x": 0.0, "y": 1.2, "z": 3.5},
                                    "radius_m": 2.0,
                                    "intent": "diffuse",
                                },
                            ],
                        },
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
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_dimensions_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_id_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_class_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_profile_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["surface_treatment_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["surface_treatment_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_absorption_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_diffusion_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reflection_policy_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reflection_policy_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_reflection_style_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_early_reflections_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_late_reverb_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["renderer_adaptation_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["renderer_adaptation_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_target_playback_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_spatial_priority_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_downmix_policy_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zones_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zone_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_intents_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_intents_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_roles_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_roles_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speakers_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_channels_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_roles_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_roles_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_roles_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_coverage_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["active_channels_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_active_channels_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_active_channels_count_delta"], 0)

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
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_source_groups_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_source_groups_count_delta"], 1)

    def test_arwif_batch_diff_analyze_tracks_geometry_reference_presence_changed_pairs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "geometry-reference-presence-left.yaml"
            right_spec_path = tmp_dir / "geometry-reference-presence-right.yaml"
            left_artifact_path = tmp_dir / "geometry-reference-presence-left.arwif"
            right_artifact_path = tmp_dir / "geometry-reference-presence-right.arwif"
            diff_report_path = tmp_dir / "geometry-reference-presence-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Geometry reference presence left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Geometry reference presence right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "  geometry_reference:",
                        "    geometry_id: studio-a",
                        "    geometry_class: shoebox",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(
                repo_root,
                "arwif-diff",
                str(left_artifact_path),
                str(right_artifact_path),
                "--json",
            )
            self.assertFalse(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["geometry_reference_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["geometry_reference_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_geometry_id_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_geometry_class_changed"])

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_present_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["geometry_reference_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_id_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_geometry_class_changed_pairs"], 1)

    def test_arwif_batch_diff_analyze_tracks_surface_treatment_presence_changed_pairs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "surface-treatment-presence-left.yaml"
            right_spec_path = tmp_dir / "surface-treatment-presence-right.yaml"
            left_artifact_path = tmp_dir / "surface-treatment-presence-left.arwif"
            right_artifact_path = tmp_dir / "surface-treatment-presence-right.arwif"
            diff_report_path = tmp_dir / "surface-treatment-presence-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Surface treatment presence left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Surface treatment presence right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "  surface_treatment:",
                        "    absorption: balanced",
                        "    diffusion: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["surface_treatment_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["surface_treatment_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_surface_absorption_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_surface_diffusion_changed"])

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["surface_treatment_present_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["surface_treatment_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_absorption_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_surface_diffusion_changed_pairs"], 1)

    def test_arwif_batch_diff_analyze_tracks_reflection_policy_presence_changed_pairs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "reflection-policy-presence-left.yaml"
            right_spec_path = tmp_dir / "reflection-policy-presence-right.yaml"
            left_artifact_path = tmp_dir / "reflection-policy-presence-left.arwif"
            right_artifact_path = tmp_dir / "reflection-policy-presence-right.arwif"
            diff_report_path = tmp_dir / "reflection-policy-presence-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Reflection policy presence left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Reflection policy presence right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "  reflection_policy:",
                        "    style: balanced",
                        "    early_reflections: natural",
                        "    late_reverb: controlled",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["reflection_policy_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["reflection_policy_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_reflection_style_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_early_reflections_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_late_reverb_changed"])

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reflection_policy_present_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["reflection_policy_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_reflection_style_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_early_reflections_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_late_reverb_changed_pairs"], 1)

    def test_arwif_batch_diff_analyze_tracks_renderer_adaptation_presence_changed_pairs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "renderer-adaptation-presence-left.yaml"
            right_spec_path = tmp_dir / "renderer-adaptation-presence-right.yaml"
            left_artifact_path = tmp_dir / "renderer-adaptation-presence-left.arwif"
            right_artifact_path = tmp_dir / "renderer-adaptation-presence-right.arwif"
            diff_report_path = tmp_dir / "renderer-adaptation-presence-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Renderer adaptation presence left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Renderer adaptation presence right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "  renderer_adaptation_hints:",
                        "    target_playback: headphones",
                        "    spatial_priority: precision",
                        "    downmix_policy: preserve_positions",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["renderer_adaptation_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["renderer_adaptation_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_target_playback_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_spatial_priority_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_downmix_policy_changed"])

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["renderer_adaptation_present_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["renderer_adaptation_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_target_playback_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_spatial_priority_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_downmix_policy_changed_pairs"], 1)

    def test_arwif_batch_diff_analyze_tracks_max_frequency_hz_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "max-frequency-left.arwif"
            right_path = tmp_dir / "max-frequency-right.arwif"
            diff_report_path = tmp_dir / "max-frequency-batch-diff.json"

            save_wave_library(
                left_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(220, 0.8), AtomicWaveUnit(330, 0.5)),
                            label="base",
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "title": "Max frequency left",
                    },
                ),
            )

            save_wave_library(
                right_path,
                WaveLibrary(
                    states=(
                        WaveState(
                            vector_length=512,
                            units=(AtomicWaveUnit(220, 0.8), AtomicWaveUnit(440, 0.5)),
                            label="base",
                        ),
                    ),
                    metadata={
                        "format": "arwif_audio",
                        "arwif_version": 1,
                        "frequency_unit": "hz",
                        "playback_model": "continuous_oscillator_bank",
                        "sample_rate_hz": 8000,
                        "default_duration_seconds": 0.25,
                        "title": "Max frequency right",
                    },
                ),
            )

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(diff_payload["oscillator_count_delta"], 0)
            self.assertEqual(diff_payload["state_count_delta"], 0)
            self.assertEqual(diff_payload["max_frequency_hz_delta"], 110)

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
            self.assertEqual(analysis_payload["changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_max_frequency_hz_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_max_frequency_hz_delta"], 110)

    def test_arwif_batch_diff_analyze_tracks_intent_count_deltas(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "intent-count-left.yaml"
            right_spec_path = tmp_dir / "intent-count-right.yaml"
            left_artifact_path = tmp_dir / "intent-count-left.arwif"
            right_artifact_path = tmp_dir / "intent-count-right.arwif"
            diff_report_path = tmp_dir / "intent-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Intent count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  listening_zones:",
                        "    - zone_id: sweet-spot",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 1.2",
                        "        z: 0.0",
                        "      radius_m: 1.5",
                        "      intent: focused",
                        "    - zone_id: couch",
                        "      anchor:",
                        "        x: 1.5",
                        "        y: 1.2",
                        "        z: -0.5",
                        "      radius_m: 2.0",
                        "      intent: focused",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Intent count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  listening_zones:",
                        "    - zone_id: sweet-spot",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 1.2",
                        "        z: 0.0",
                        "      radius_m: 1.5",
                        "      intent: focused",
                        "    - zone_id: couch",
                        "      anchor:",
                        "        x: 1.5",
                        "        y: 1.2",
                        "        z: -0.5",
                        "      radius_m: 2.0",
                        "      intent: diffuse",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: wide",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["listening_zones_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["listening_zone_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_intents_count_delta"], 1)
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["speaker_coverage_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_coverage_intents_count_delta"], 1)
            self.assertEqual(diff_payload["spatial_changes"]["speaker_count_delta"], 0)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zone_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_intents_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_intents_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_coverage_intents_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_coverage_intents_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_coverage_intents_count_delta"], 1)

    def test_arwif_batch_diff_analyze_tracks_speaker_roles_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "speaker-roles-count-left.yaml"
            right_spec_path = tmp_dir / "speaker-roles-count-right.yaml"
            left_artifact_path = tmp_dir / "speaker-roles-count-left.arwif"
            right_artifact_path = tmp_dir / "speaker-roles-count-right.arwif"
            diff_report_path = tmp_dir / "speaker-roles-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker roles count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker roles count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: surround",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["speaker_roles_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_roles_count_delta"], 1)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_coverage_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["speaker_count_delta"], 0)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_roles_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_roles_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_roles_count_delta"], 1)

    def test_arwif_batch_diff_analyze_tracks_speaker_channels_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "speaker-channels-count-left.yaml"
            right_spec_path = tmp_dir / "speaker-channels-count-right.yaml"
            left_artifact_path = tmp_dir / "speaker-channels-count-left.arwif"
            right_artifact_path = tmp_dir / "speaker-channels-count-right.arwif"
            diff_report_path = tmp_dir / "speaker-channels-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker channels count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker channels count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["speaker_channels_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_channels_count_delta"], 1)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_roles_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_roles_count_delta"], 0)
            self.assertFalse(diff_payload["spatial_changes"]["speaker_coverage_intents_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_coverage_intents_count_delta"], 0)
            self.assertEqual(diff_payload["spatial_changes"]["speaker_count_delta"], 0)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_channels_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_channels_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_channels_count_delta"], 1)

    def test_arwif_batch_diff_analyze_tracks_active_channels_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "active-channels-count-left.yaml"
            right_spec_path = tmp_dir / "active-channels-count-right.yaml"
            left_artifact_path = tmp_dir / "active-channels-count-left.arwif"
            right_artifact_path = tmp_dir / "active-channels-count-right.arwif"
            diff_report_path = tmp_dir / "active-channels-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Active channels count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "states:",
                        "  - label: base",
                        "    channel_gains:",
                        "      L: 1.0",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Active channels count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "states:",
                        "  - label: base",
                        "    channel_gains:",
                        "      L: 1.0",
                        "      R: 0.5",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertFalse(diff_payload["spatial_changes"]["channel_layout_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["active_channels_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["active_channels_count_delta"], 1)
            self.assertEqual(diff_payload["spatial_changes"]["states_with_channel_gains_delta"], 0)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["active_channels_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_active_channels_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_active_channels_count_delta"], 1)

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


class ARWIFSpeakerSpatialIntegrationTest(unittest.TestCase):
    def test_arwif_diff_reports_speaker_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "left-speaker-id.yaml"
            right_spec_path = tmp_dir / "right-speaker-id.yaml"
            left_artifact_path = tmp_dir / "left-speaker-id.arwif"
            right_artifact_path = tmp_dir / "right-speaker-id.arwif"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker id left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker id right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-alt",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertTrue(diff_payload["spatial_changes"]["speaker_ids_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_ids_count_delta"], 0)
            self.assertTrue(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertFalse(diff_payload["spatial_changes"]["speaker_roles_changed"])

    def test_arwif_batch_diff_analysis_reports_speaker_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "left-batch-speaker-id.yaml"
            right_spec_path = tmp_dir / "right-batch-speaker-id.yaml"
            left_artifact_path = tmp_dir / "left-batch-speaker-id.arwif"
            right_artifact_path = tmp_dir / "right-batch-speaker-id.arwif"
            diff_report_path = tmp_dir / "speaker-id-batch-diff.json"
            analysis_report_path = tmp_dir / "speaker-id-batch-analysis.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker id batch left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker id batch right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-alt",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "arwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speakers_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_channels_count_delta"], 0)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_channels_count_delta"], 0)
            self.assertTrue(analysis_report_path.exists())

    def test_arwif_batch_diff_analyze_tracks_listening_zone_ids_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "listening-zone-ids-count-left.yaml"
            right_spec_path = tmp_dir / "listening-zone-ids-count-right.yaml"
            left_artifact_path = tmp_dir / "listening-zone-ids-count-left.arwif"
            right_artifact_path = tmp_dir / "listening-zone-ids-count-right.arwif"
            diff_report_path = tmp_dir / "listening-zone-ids-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Listening zone ids count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  listening_zones:",
                        "    - zone_id: nearfield",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 0.0",
                        "        z: 0.0",
                        "      radius_m: 1.0",
                        "      intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Listening zone ids count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  listening_zones:",
                        "    - zone_id: nearfield",
                        "      anchor:",
                        "        x: 0.0",
                        "        y: 0.0",
                        "        z: 0.0",
                        "      radius_m: 1.0",
                        "      intent: focused",
                        "    - zone_id: audience",
                        "      anchor:",
                        "        x: 1.5",
                        "        y: 0.0",
                        "        z: -0.5",
                        "      radius_m: 2.0",
                        "      intent: diffuse",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertTrue(diff_payload["spatial_changes"]["listening_zones_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_ids_count_delta"], 1)
            self.assertEqual(diff_payload["spatial_changes"]["listening_zone_count_delta"], 1)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["listening_zones_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_listening_zone_ids_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_listening_zone_ids_count_delta"], 1)

    def test_arwif_batch_diff_analyze_tracks_speaker_ids_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "speaker-ids-count-left.yaml"
            right_spec_path = tmp_dir / "speaker-ids-count-right.yaml"
            left_artifact_path = tmp_dir / "speaker-ids-count-left.arwif"
            right_artifact_path = tmp_dir / "speaker-ids-count-right.arwif"
            diff_report_path = tmp_dir / "speaker-ids-count-batch-diff.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker ids count left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Speaker ids count right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "channel_layout: stereo",
                        "room:",
                        "  speakers:",
                        "    - speaker_id: left-main",
                        "      anchor:",
                        "        x: -2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: L",
                        "      role: main",
                        "      coverage_intent: focused",
                        "    - speaker_id: right-main",
                        "      anchor:",
                        "        x: 2.5",
                        "        y: 1.3",
                        "        z: 2.0",
                        "      channel: R",
                        "      role: main",
                        "      coverage_intent: focused",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertTrue(diff_payload["spatial_changes"]["speaker_ids_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_ids_count_delta"], 1)
            self.assertTrue(diff_payload["spatial_changes"]["speakers_changed"])
            self.assertEqual(diff_payload["spatial_changes"]["speaker_count_delta"], 1)

            self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )

            analysis_payload = self._run_json(repo_root, "arwif-batch-diff-analyze", str(diff_report_path), "--json")
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["speaker_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["pairs_with_speaker_ids_count_delta"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["total_speaker_ids_count_delta"], 1)

    def test_arwif_diff_reports_room_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "left-room-presence.yaml"
            right_spec_path = tmp_dir / "right-room-presence.yaml"
            left_artifact_path = tmp_dir / "left-room-presence.arwif"
            right_artifact_path = tmp_dir / "right-room-presence.arwif"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Room presence left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Room presence right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(repo_root, "arwif-diff", str(left_artifact_path), str(right_artifact_path), "--json")
            self.assertTrue(diff_payload["spatial_changes"]["room_present_changed"])
            self.assertTrue(diff_payload["spatial_changes"]["room_changed"])

    def test_arwif_batch_diff_analysis_reports_room_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_spec_path = tmp_dir / "left-batch-room-presence.yaml"
            right_spec_path = tmp_dir / "right-batch-room-presence.yaml"
            left_artifact_path = tmp_dir / "left-batch-room-presence.arwif"
            right_artifact_path = tmp_dir / "right-batch-room-presence.arwif"
            diff_report_path = tmp_dir / "room-presence-batch-diff.json"
            analysis_report_path = tmp_dir / "room-presence-batch-analysis.json"

            left_spec_path.write_text(
                "\n".join(
                    [
                        "title: Room presence batch left",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_spec_path.write_text(
                "\n".join(
                    [
                        "title: Room presence batch right",
                        "sample_rate_hz: 8000",
                        "default_duration_seconds: 0.25",
                        "room:",
                        "  dimensions:",
                        "    width_m: 6.0",
                        "    depth_m: 8.0",
                        "    height_m: 3.0",
                        "states:",
                        "  - label: base",
                        "    oscillators:",
                        "      - hz: 220",
                        "        amplitude: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self._run_json(repo_root, "arwif-build", "--spec", str(left_spec_path), "--output", str(left_artifact_path), "--json")
            self._run_json(repo_root, "arwif-build", "--spec", str(right_spec_path), "--output", str(right_artifact_path), "--json")

            diff_payload = self._run_json(
                repo_root,
                "arwif-batch-diff",
                "--left",
                str(left_artifact_path),
                "--right",
                str(right_artifact_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "arwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_present_changed_pairs"], 1)
            self.assertEqual(analysis_payload["spatial_change_summary"]["room_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_arwif_analyze_audio_reports_basic_observation_for_wav(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            wav_path = tmp_dir / "analysis-input.wav"
            analysis_output_path = tmp_dir / "analysis-output.yaml"
            report_output_path = tmp_dir / "analysis-report.json"

            sample_rate_hz = 8000
            duration_seconds = 0.25
            frame_count = int(sample_rate_hz * duration_seconds)
            samples: list[int] = []
            for frame_index in range(frame_count):
                time_position = frame_index / float(sample_rate_hz)
                left_sample = int(round(0.6 * 32767.0 * math.sin(2.0 * math.pi * 220.0 * time_position)))
                right_sample = int(round(0.4 * 32767.0 * math.sin(2.0 * math.pi * 330.0 * time_position)))
                samples.extend((left_sample, right_sample))

            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate_hz)
                frame_bytes = bytearray()
                for sample in samples:
                    frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-analyze-audio",
                str(wav_path),
                "--output",
                str(analysis_output_path),
                "--report",
                str(report_output_path),
                "--source-id",
                "demo.clip-01",
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["command"], "arwif-analyze-audio")
            self.assertEqual(payload["analysis_profile"], "basic-observation")
            self.assertEqual(payload["source_id"], "demo.clip-01")
            self.assertEqual(payload["decoded_audio"]["sample_rate_hz"], sample_rate_hz)
            self.assertEqual(payload["decoded_audio"]["channel_count"], 2)
            self.assertEqual(payload["decoded_audio"]["decode_backend"], "wave")
            self.assertGreater(payload["observation_summary"]["peak_amplitude"], 0.0)
            self.assertEqual(payload["analysis_document_format"], "yaml")
            self.assertEqual(payload["report_format"], "json")
            self.assertTrue(analysis_output_path.exists())
            self.assertTrue(report_output_path.exists())

            analysis_document = yaml.safe_load(analysis_output_path.read_text(encoding="utf-8"))
            self.assertEqual(analysis_document["analysis_metadata"]["analysis_profile"], "basic-observation")
            self.assertEqual(analysis_document["observed_audio"]["channel_count"], 2)
            self.assertIn("basic_observation_summary", analysis_document["observation_layers"])
            self.assertIn("onset_map", analysis_document["observation_layers"])
            self.assertIn("section_boundaries", analysis_document["observation_layers"])
            self.assertIn("section_candidates", analysis_document["observation_layers"])
            self.assertGreater(len(analysis_document["observation_layers"]["onset_map"]), 0)
            self.assertIn("section_profile_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_profile_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_sequence_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_chain_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_family_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_archetype_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_contour_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_sweep_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_gesture_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_mobility_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("section_transitions", analysis_document["observation_layers"])

            report_document = json.loads(report_output_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["source_id"], "demo.clip-01")
            self.assertEqual(report_document["decoded_audio"]["channel_mode"], "preserve")
            self.assertIn("observation_preview", report_document)
            self.assertIn("section_candidate_count", report_document["observation_preview"])
            self.assertIn("section_profile_summary", report_document["observation_preview"])
            self.assertIn("transition_profile_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_sequence_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_chain_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_family_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_archetype_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_contour_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_sweep_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_gesture_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_mobility_summary", report_document["observation_preview"])
            self.assertIn("transition_motif_phrase_abstraction_ladder", report_document["observation_preview"])

    def test_arwif_analyze_audio_supports_excerpt_and_mono_mode(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            wav_path = tmp_dir / "analysis-window.wav"

            sample_rate_hz = 4000
            duration_seconds = 1.0
            frame_count = int(sample_rate_hz * duration_seconds)
            samples: list[int] = []
            for frame_index in range(frame_count):
                time_position = frame_index / float(sample_rate_hz)
                sample = int(round(0.5 * 32767.0 * math.sin(2.0 * math.pi * 180.0 * time_position)))
                samples.append(sample)

            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate_hz)
                frame_bytes = bytearray()
                for sample in samples:
                    frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-analyze-audio",
                str(wav_path),
                "--start-seconds",
                "0.2",
                "--duration-seconds",
                "0.3",
                "--channel-mode",
                "mono",
                "--target-sample-rate-hz",
                "2000",
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["decoded_audio"]["channel_count"], 1)
            self.assertEqual(payload["decoded_audio"]["sample_rate_hz"], 2000)
            self.assertAlmostEqual(payload["analysis_window"]["duration_seconds"], 0.3, places=2)
            self.assertGreaterEqual(len(payload["warnings"]), 1)

    def test_arwif_analyze_audio_populates_section_boundaries_for_changed_energy_regions(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            wav_path = tmp_dir / "analysis-sections.wav"
            analysis_output_path = tmp_dir / "analysis-sections.yaml"

            sample_rate_hz = 4000
            sections = [
                (0.35, 0.0),
                (0.35, 0.45),
                (0.35, 0.1),
            ]
            samples: list[int] = []
            for duration_seconds, amplitude in sections:
                frame_count = int(sample_rate_hz * duration_seconds)
                for frame_index in range(frame_count):
                    time_position = frame_index / float(sample_rate_hz)
                    sample = int(round(amplitude * 32767.0 * math.sin(2.0 * math.pi * 220.0 * time_position)))
                    samples.append(sample)

            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate_hz)
                frame_bytes = bytearray()
                for sample in samples:
                    frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-analyze-audio",
                str(wav_path),
                "--output",
                str(analysis_output_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertGreaterEqual(payload["observation_summary"]["section_boundary_count"], 1)
            self.assertGreaterEqual(payload["observation_summary"]["section_candidate_count"], 1)
            analysis_document = yaml.safe_load(analysis_output_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(analysis_document["observation_layers"]["section_boundaries"]), 1)
            self.assertGreaterEqual(len(analysis_document["observation_layers"]["section_candidates"]), 1)
            first_boundary = analysis_document["observation_layers"]["section_boundaries"][0]
            self.assertIn("offset_seconds", first_boundary)
            self.assertIn("confidence", first_boundary)
            first_candidate = analysis_document["observation_layers"]["section_candidates"][0]
            self.assertIn("start_seconds", first_candidate)
            self.assertIn("duration_seconds", first_candidate)
            self.assertIn("energy_band", first_candidate)
            self.assertIn("duration_band", first_candidate)
            self.assertIn("position_band", first_candidate)
            self.assertIn("section_profile_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_profile_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_sequence_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_chain_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_family_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertIn("transition_motif_phrase_archetype_summary", analysis_document["observation_layers"]["basic_observation_summary"])
            self.assertGreaterEqual(len(analysis_document["observation_layers"]["section_transitions"]), 1)
            self.assertGreaterEqual(payload["source_hypothesis_count"], 1)
            self.assertIn("sustained_sectional_bed", payload["source_hypothesis_classes"])
            self.assertGreaterEqual(len(analysis_document["source_hypotheses"]), 1)
            self.assertEqual(analysis_document["source_hypotheses"][0]["hypothesis_origin"], "observation-derived")
            self.assertIn("time_bounds", analysis_document["source_hypotheses"][0])
            self.assertIn("linked_observations", analysis_document["source_hypotheses"][0])
            first_transition = analysis_document["observation_layers"]["section_transitions"][0]
            self.assertIn("transition_kind", first_transition)
            self.assertIn("energy_delta", first_transition)

    def test_arwif_analyze_audio_emits_workspace_task_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            wav_path = tmp_dir / "analysis-workspace.wav"
            analysis_output_path = tmp_dir / "analysis-workspace.yaml"
            report_output_path = tmp_dir / "analysis-workspace-report.json"

            sample_rate_hz = 4000
            frame_count = int(sample_rate_hz * 0.25)
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate_hz)
                frame_bytes = bytearray()
                for frame_index in range(frame_count):
                    sample = int(round(0.45 * 32767.0 * math.sin(2.0 * math.pi * 220.0 * (frame_index / 4000.0))))
                    frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-analyze-audio",
                str(wav_path),
                "--output",
                str(analysis_output_path),
                "--report",
                str(report_output_path),
                "--query-text",
                "Keep the backing bed, suppress the foreground call, and summarize what remains.",
                "--attention-target",
                "backing_bed",
                "--attention-target",
                "foreground_call_stream",
                "--retain-target",
                "backing_bed",
                "--suppress-target",
                "foreground_call_stream",
                "--answer-expectation",
                "summarize remaining scene",
                "--render-goal",
                "backing bed without foreground call stream",
                "--transform-operation",
                "retain",
                "--transform-operation",
                "suppress",
                "--transform-operation",
                "summarize",
                "--primary-output",
                "backing_bed_without_foreground_call_stream",
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(
                payload["attention_contract"],
                {
                    "query_text": "Keep the backing bed, suppress the foreground call, and summarize what remains.",
                    "attention_targets": ["backing_bed", "foreground_call_stream"],
                    "retain_targets": ["backing_bed"],
                    "suppress_targets": ["foreground_call_stream"],
                    "answer_expectations": ["summarize remaining scene"],
                    "render_goal": "backing bed without foreground call stream",
                },
            )
            self.assertEqual(
                payload["transformation_intent"],
                {
                    "operations": ["retain", "suppress", "summarize"],
                    "primary_output": "backing_bed_without_foreground_call_stream",
                },
            )
            self.assertEqual(
                payload["interpretation_layers"]["scene_hypotheses"][0]["hypothesis_origin"],
                "task-conditioned-observation-summary",
            )
            self.assertEqual(
                payload["interpretation_layers"]["task_conditioning_notes"]["status"],
                "task-conditioned",
            )
            self.assertEqual(payload["interpretation_layers"]["communicative_hypotheses"], [])

            analysis_document = yaml.safe_load(analysis_output_path.read_text(encoding="utf-8"))
            self.assertEqual(analysis_document["attention_contract"], payload["attention_contract"])
            self.assertEqual(analysis_document["interpretation_layers"], payload["interpretation_layers"])
            self.assertEqual(analysis_document["transformation_intent"], payload["transformation_intent"])

            report_document = json.loads(report_output_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["attention_contract"], payload["attention_contract"])
            self.assertEqual(report_document["interpretation_layers"], payload["interpretation_layers"])
            self.assertEqual(report_document["transformation_intent"], payload["transformation_intent"])

    def test_arwif_batch_analyze_audio_persists_per_input_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_wav_path = tmp_dir / "alpha.wav"
            second_wav_path = tmp_dir / "beta.wav"
            analysis_dir = tmp_dir / "analysis-documents"
            report_dir = tmp_dir / "analysis-reports"
            aggregate_report_path = tmp_dir / "batch-analysis-report.json"

            for wav_path, sample_rate_hz, frequency_hz in (
                (first_wav_path, 8000, 220.0),
                (second_wav_path, 12000, 330.0),
            ):
                frame_count = int(sample_rate_hz * 0.2)
                samples: list[int] = []
                for frame_index in range(frame_count):
                    time_position = frame_index / float(sample_rate_hz)
                    sample = int(round(0.5 * 32767.0 * math.sin(2.0 * math.pi * frequency_hz * time_position)))
                    samples.append(sample)
                with wave.open(str(wav_path), "wb") as handle:
                    handle.setnchannels(1)
                    handle.setsampwidth(2)
                    handle.setframerate(sample_rate_hz)
                    frame_bytes = bytearray()
                    for sample in samples:
                        frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                    handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-batch-analyze-audio",
                str(first_wav_path),
                str(second_wav_path),
                "--analysis-dir",
                str(analysis_dir),
                "--report-dir",
                str(report_dir),
                "--query-text",
                "Retain the backing bed and suppress the foreground call across the batch.",
                "--attention-target",
                "backing_bed",
                "--attention-target",
                "foreground_call_stream",
                "--retain-target",
                "backing_bed",
                "--suppress-target",
                "foreground_call_stream",
                "--transform-operation",
                "retain",
                "--transform-operation",
                "suppress",
                "--primary-output",
                "backing_bed_without_foreground_call_stream",
                "--output",
                str(aggregate_report_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["audio_inputs_processed"], 2)
            self.assertEqual(payload["valid_count"], 2)
            self.assertEqual(payload["invalid_count"], 0)
            self.assertEqual(payload["analysis_dir"], str(analysis_dir))
            self.assertEqual(payload["report_dir"], str(report_dir))
            self.assertEqual(payload["analysis_format"], "yaml")
            self.assertEqual(payload["report_format"], "json")
            self.assertEqual(payload["aggregate_report_format"], "json")
            self.assertEqual(
                payload["attention_contract"]["query_text"],
                "Retain the backing bed and suppress the foreground call across the batch.",
            )
            self.assertEqual(
                payload["attention_contract"]["attention_targets"],
                ["backing_bed", "foreground_call_stream"],
            )
            self.assertEqual(payload["transformation_intent"]["operations"], ["retain", "suppress"])
            self.assertEqual(
                payload["transformation_intent"]["primary_output"],
                "backing_bed_without_foreground_call_stream",
            )
            self.assertEqual(payload["decode_backends"], ["wave"])
            self.assertEqual(payload["max_channel_count"], 1)
            self.assertGreaterEqual(payload["total_section_boundary_count"], 0)
            self.assertGreaterEqual(payload["total_section_candidate_count"], 0)
            self.assertGreaterEqual(payload["total_section_transition_count"], 0)
            self.assertIn("total_section_energy_band_counts", payload)
            self.assertIn("total_section_duration_band_counts", payload)
            self.assertIn("total_section_position_band_counts", payload)
            self.assertIn("total_transition_kind_counts", payload)
            self.assertTrue(aggregate_report_path.exists())
            self.assertEqual(len(payload["results"]), 2)

            persisted_report = json.loads(aggregate_report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["audio_inputs_processed"], 2)
            self.assertEqual(persisted_report["valid_count"], 2)
            self.assertEqual(persisted_report["attention_contract"]["retain_targets"], ["backing_bed"])

            self.assertTrue((analysis_dir / "alpha.analysis.yaml").exists())
            self.assertTrue((analysis_dir / "beta.analysis.yaml").exists())
            self.assertTrue((report_dir / "alpha.report.json").exists())
            self.assertTrue((report_dir / "beta.report.json").exists())
            first_analysis_document = yaml.safe_load((analysis_dir / "alpha.analysis.yaml").read_text(encoding="utf-8"))
            self.assertEqual(first_analysis_document["attention_contract"]["suppress_targets"], ["foreground_call_stream"])
            self.assertEqual(first_analysis_document["interpretation_layers"]["task_conditioning_notes"]["status"], "task-conditioned")
            first_report_document = json.loads((report_dir / "alpha.report.json").read_text(encoding="utf-8"))
            self.assertIn("scene_hypotheses", first_report_document["interpretation_layers"])
            self.assertEqual(
                first_report_document["transformation_intent"]["primary_output"],
                "backing_bed_without_foreground_call_stream",
            )

    def test_arwif_batch_analyze_audio_reports_failures(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            wav_path = tmp_dir / "valid.wav"
            missing_path = tmp_dir / "missing.wav"
            frame_count = 800
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                frame_bytes = bytearray()
                for frame_index in range(frame_count):
                    sample = int(round(0.4 * 32767.0 * math.sin(2.0 * math.pi * 220.0 * (frame_index / 8000.0))))
                    frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frame_bytes))

            payload = self._run_json(
                repo_root,
                "arwif-batch-analyze-audio",
                str(wav_path),
                str(missing_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"], payload)
            self.assertEqual(payload["audio_inputs_processed"], 2)
            self.assertEqual(payload["valid_count"], 1)
            self.assertEqual(payload["invalid_count"], 1)
            invalid_result = next(result for result in payload["results"] if result["input_audio"] == str(missing_path))
            self.assertFalse(invalid_result["is_valid"])
            self.assertIn("does not exist", invalid_result["errors"][0])

    def test_arwif_inspect_analysis_summarizes_yaml_document(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "analysis-output.yaml"

            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "demo.analysis-01",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/example.wav",
                            "duration_seconds": 12.5,
                            "sample_rate_hz": 16000,
                            "channel_count": 2,
                            "codec": "wav",
                            "original_sample_rate_hz": 16000,
                            "original_channel_count": 2,
                            "analysis_window": {
                                "start_seconds": 1.5,
                                "duration_seconds": 4.0,
                            },
                        },
                        "observation_layers": {
                            "basic_observation_summary": {
                                "peak_amplitude": 0.42,
                                "rms_amplitude": 0.13,
                                "estimated_onset_count": 9,
                                "section_candidate_count": 0,
                                "section_profile_summary": {
                                    "average_duration_seconds": 0.0,
                                    "longest_duration_seconds": 0.0,
                                    "energy_band_counts": {},
                                    "duration_band_counts": {},
                                    "position_band_counts": {},
                                    "dominant_energy_band": None,
                                    "opening_energy_band": None,
                                    "closing_energy_band": None,
                                },
                                "transition_profile_summary": {
                                    "average_abs_energy_delta": 0.0,
                                    "largest_abs_energy_delta": 0.0,
                                    "transition_kind_counts": {},
                                    "dominant_transition_kind": None,
                                    "opening_transition_kind": None,
                                    "closing_transition_kind": None,
                                },
                                "transition_motif_summary": {
                                    "recurring_motif_count": 0,
                                    "motif_occurrence_count": 0,
                                    "motif_signature_counts": {},
                                    "motif_signatures": [],
                                    "dominant_motif_signature": None,
                                    "motifs": [],
                                },
                                "transition_motif_sequence_summary": {
                                    "recurring_sequence_count": 0,
                                    "sequence_occurrence_count": 0,
                                    "sequence_signature_counts": {},
                                    "sequence_signatures": [],
                                    "dominant_sequence_signature": None,
                                    "sequences": [],
                                },
                                "transition_motif_chain_summary": {
                                    "chain_length": 3,
                                    "recurring_chain_count": 0,
                                    "chain_occurrence_count": 0,
                                    "chain_signature_counts": {},
                                    "chain_signatures": [],
                                    "dominant_chain_signature": None,
                                    "chains": [],
                                },
                                "transition_motif_phrase_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_phrase_count": 0,
                                    "phrase_occurrence_count": 0,
                                    "phrase_signature_counts": {},
                                    "phrase_signatures": [],
                                    "dominant_phrase_signature": None,
                                    "phrases": [],
                                },
                                "transition_motif_phrase_family_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_family_count": 0,
                                    "family_occurrence_count": 0,
                                    "family_signature_counts": {},
                                    "family_signatures": [],
                                    "dominant_family_signature": None,
                                    "families": [],
                                },
                                "transition_motif_phrase_archetype_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_archetype_count": 0,
                                    "archetype_occurrence_count": 0,
                                    "archetype_signature_counts": {},
                                    "archetype_signatures": [],
                                    "dominant_archetype_signature": None,
                                    "archetypes": [],
                                },
                                "transition_motif_phrase_contour_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_contour_count": 0,
                                    "contour_occurrence_count": 0,
                                    "contour_signature_counts": {},
                                    "contour_signatures": [],
                                    "dominant_contour_signature": None,
                                    "contours": [],
                                },
                                "transition_motif_phrase_sweep_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_sweep_count": 0,
                                    "sweep_occurrence_count": 0,
                                    "sweep_signature_counts": {},
                                    "sweep_signatures": [],
                                    "dominant_sweep_signature": None,
                                    "sweeps": [],
                                },
                                "transition_motif_phrase_gesture_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_gesture_count": 0,
                                    "gesture_occurrence_count": 0,
                                    "gesture_signature_counts": {},
                                    "gesture_signatures": [],
                                    "dominant_gesture_signature": None,
                                    "gestures": [],
                                },
                                "transition_motif_phrase_mobility_summary": {
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 5,
                                    "recurring_mobility_count": 0,
                                    "mobility_occurrence_count": 0,
                                    "mobility_signature_counts": {},
                                    "mobility_signatures": [],
                                    "dominant_mobility_signature": None,
                                    "mobilities": [],
                                },
                            },
                                    "onset_map": [],
                            "transient_events": [],
                            "section_boundaries": [],
                                    "section_candidates": [],
                                    "section_transitions": [],
                        },
                        "source_hypotheses": [
                            {"source_id": "source.vocal.01", "source_class": "lead_vocal", "role": "principal", "time_bounds": {"start_seconds": 1.5, "end_seconds": 4.5, "duration_seconds": 3.0}, "linked_observations": {"section_indexes": [0], "transition_indexes": [], "transition_motif_ids": ["transition_motif.01"], "transition_motif_signatures": ["energy_stable|medium|medium|stable"], "transition_motif_reference_count": 1, "transition_motif_sequence_ids": ["transition_motif_sequence.01"], "transition_motif_sequence_signatures": ["energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable"], "transition_motif_sequence_reference_count": 1, "transition_motif_chain_ids": [], "transition_motif_chain_signatures": [], "transition_motif_chain_reference_count": 0, "transition_motif_phrase_ids": [], "transition_motif_phrase_signatures": [], "transition_motif_phrase_reference_count": 0, "transition_motif_phrase_family_ids": [], "transition_motif_phrase_family_signatures": [], "transition_motif_phrase_family_reference_count": 0, "transition_motif_phrase_archetype_ids": [], "transition_motif_phrase_archetype_signatures": [], "transition_motif_phrase_archetype_reference_count": 0, "transition_motif_phrase_contour_ids": [], "transition_motif_phrase_contour_signatures": [], "transition_motif_phrase_contour_reference_count": 0, "transition_motif_phrase_sweep_ids": [], "transition_motif_phrase_sweep_signatures": [], "transition_motif_phrase_sweep_reference_count": 0, "transition_motif_phrase_gesture_ids": [], "transition_motif_phrase_gesture_signatures": [], "transition_motif_phrase_gesture_reference_count": 0, "transition_motif_phrase_mobility_ids": [], "transition_motif_phrase_mobility_signatures": [], "transition_motif_phrase_mobility_reference_count": 0, "onset_offsets_seconds_preview": [1.8], "onset_reference_count": 1}},
                            {"source_id": "source.backing.01", "source_class": "backing_vocal", "role": "support", "time_bounds": {"start_seconds": 2.0, "end_seconds": 5.0, "duration_seconds": 3.0}, "linked_observations": {"section_indexes": [0], "transition_indexes": [], "transition_motif_ids": [], "transition_motif_signatures": [], "transition_motif_reference_count": 0, "transition_motif_sequence_ids": [], "transition_motif_sequence_signatures": [], "transition_motif_sequence_reference_count": 0, "transition_motif_chain_ids": [], "transition_motif_chain_signatures": [], "transition_motif_chain_reference_count": 0, "transition_motif_phrase_ids": [], "transition_motif_phrase_signatures": [], "transition_motif_phrase_reference_count": 0, "transition_motif_phrase_family_ids": [], "transition_motif_phrase_family_signatures": [], "transition_motif_phrase_family_reference_count": 0, "transition_motif_phrase_archetype_ids": [], "transition_motif_phrase_archetype_signatures": [], "transition_motif_phrase_archetype_reference_count": 0, "transition_motif_phrase_contour_ids": [], "transition_motif_phrase_contour_signatures": [], "transition_motif_phrase_contour_reference_count": 0, "transition_motif_phrase_sweep_ids": [], "transition_motif_phrase_sweep_signatures": [], "transition_motif_phrase_sweep_reference_count": 0, "transition_motif_phrase_gesture_ids": [], "transition_motif_phrase_gesture_signatures": [], "transition_motif_phrase_gesture_reference_count": 0, "transition_motif_phrase_mobility_ids": [], "transition_motif_phrase_mobility_signatures": [], "transition_motif_phrase_mobility_reference_count": 0, "onset_offsets_seconds_preview": [], "onset_reference_count": 0}},
                        ],
                        "component_layers": {
                            "harmonic_component_groups": [
                                {"component_id": "component.01"},
                                {"component_id": "component.02"},
                            ],
                            "noise_component_bands": [],
                        },
                        "reconstruction": {
                            "reconstructable_outputs": ["vocals", "accompaniment"],
                        },
                        "uncertainty_notes": {
                            "warnings": ["analysis excerpt only"],
                        },
                        "provenance": {
                            "input_file_hash": "abc123",
                            "decode_backend": "wave",
                            "preprocessing_steps": ["decode", "observe"],
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["command"], "arwif-inspect-analysis")
            self.assertEqual(payload["analysis_document_format"], "yaml")
            self.assertEqual(payload["analysis_profile"], "basic-observation")
            self.assertEqual(payload["source_hypothesis_count"], 2)
            self.assertEqual(payload["source_hypothesis_classes"], ["backing_vocal", "lead_vocal"])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signature_count"], 1)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signatures"], ["energy_stable|medium|medium|stable"])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_sequence_signature_count"], 1)
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_sequence_signatures"],
                ["energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable"],
            )
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_chain_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_chain_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_family_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_family_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_archetype_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_contour_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_sweep_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_gesture_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures"], [])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_mobility_signature_count"], 0)
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_phrase_mobility_signatures"], [])
            self.assertEqual(payload["first_source_hypothesis"]["source_class"], "lead_vocal")
            self.assertEqual(payload["first_source_hypothesis"]["time_bounds"]["duration_seconds"], 3.0)
            self.assertEqual(payload["first_source_hypothesis"]["linked_observations"]["section_indexes"], [0])
            self.assertEqual(payload["first_source_hypothesis"]["linked_observations"]["transition_motif_signatures"], ["energy_stable|medium|medium|stable"])
            self.assertEqual(
                payload["first_source_hypothesis"]["linked_observations"]["transition_motif_sequence_signatures"],
                ["energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable"],
            )
            self.assertEqual(payload["first_source_hypothesis"]["linked_observations"]["transition_motif_chain_signatures"], [])
            self.assertEqual(payload["first_source_hypothesis"]["linked_observations"].get("transition_motif_phrase_signatures", []), [])
            self.assertEqual(payload["onset_map_count"], 0)
            self.assertEqual(payload["section_boundary_count"], 0)
            self.assertEqual(payload["section_candidate_count"], 0)
            self.assertEqual(payload["section_transition_count"], 0)
            self.assertEqual(payload["section_profile_summary"]["energy_band_counts"], {})
            self.assertEqual(payload["transition_profile_summary"]["transition_kind_counts"], {})
            self.assertEqual(payload["transition_motif_summary"]["recurring_motif_count"], 0)
            self.assertEqual(payload["transition_motif_sequence_summary"]["recurring_sequence_count"], 0)
            self.assertEqual(payload["transition_motif_chain_summary"]["recurring_chain_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_summary"]["recurring_phrase_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_family_summary"]["recurring_family_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_archetype_summary"]["recurring_archetype_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_contour_summary"]["recurring_contour_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_sweep_summary"]["recurring_sweep_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_gesture_summary"]["recurring_gesture_count"], 0)
            self.assertEqual(payload["transition_motif_phrase_mobility_summary"]["recurring_mobility_count"], 0)
            self.assertEqual(
                payload["transition_motif_phrase_abstraction_ladder"],
                {
                    "recurring_counts": {
                        "phrase": 0,
                        "family": 0,
                        "archetype": 0,
                        "contour": 0,
                        "sweep": 0,
                        "gesture": 0,
                        "mobility": 0,
                    },
                    "occurrence_counts": {
                        "phrase": 0,
                        "family": 0,
                        "archetype": 0,
                        "contour": 0,
                        "sweep": 0,
                        "gesture": 0,
                        "mobility": 0,
                    },
                },
            )
            self.assertEqual(
                payload["highest_stable_transition_motif_abstraction_layer"],
                {
                    "layer": "none",
                    "recurring_count": 0,
                    "occurrence_count": 0,
                },
            )
            self.assertIsNone(payload["first_onset"])
            self.assertIsNone(payload["first_section_boundary"])
            self.assertIsNone(payload["first_section_candidate"])
            self.assertIsNone(payload["first_section_transition"])
            self.assertIsNone(payload["first_transition_motif"])
            self.assertIsNone(payload["first_transition_motif_sequence"])
            self.assertIsNone(payload["first_transition_motif_chain"])
            self.assertIsNone(payload["first_transition_motif_phrase"])
            self.assertIsNone(payload["first_transition_motif_phrase_family"])
            self.assertIsNone(payload["first_transition_motif_phrase_archetype"])
            self.assertIsNone(payload["first_transition_motif_phrase_contour"])
            self.assertIsNone(payload["first_transition_motif_phrase_sweep"])
            self.assertIsNone(payload["first_transition_motif_phrase_gesture"])
            self.assertIsNone(payload["first_transition_motif_phrase_mobility"])
            self.assertEqual(payload["component_group_count"], 2)
            self.assertEqual(payload["reconstructable_outputs"], ["vocals", "accompaniment"])
            self.assertEqual(payload["uncertainty_warning_count"], 1)
            self.assertEqual(payload["provenance_summary"]["decode_backend"], "wave")
            self.assertIn("basic_observation_summary", payload["observation_layer_names"])

    def test_arwif_inspect_analysis_summarizes_workspace_sections_when_present(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "workspace-analysis.yaml"

            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "workspace.demo-01",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/example.wav",
                            "duration_seconds": 8.0,
                            "sample_rate_hz": 16000,
                            "channel_count": 1,
                            "codec": "wav",
                            "original_sample_rate_hz": 16000,
                            "original_channel_count": 1,
                        },
                        "attention_contract": {
                            "query_text": "Keep accompaniment, suppress vocals, and summarize likely crowd interjections.",
                            "attention_targets": ["lead_vocal", "backing_band", "crowd_noise"],
                            "retain_targets": ["backing_band"],
                            "suppress_targets": ["lead_vocal"],
                            "answer_expectations": ["summarize crowd interjections"],
                            "render_goal": "instrumental bed with crowd-notes sidecar",
                        },
                        "observation_layers": {
                            "basic_observation_summary": {},
                            "onset_map": [],
                            "section_boundaries": [],
                            "section_candidates": [],
                            "section_transitions": [],
                        },
                        "source_hypotheses": [],
                        "interpretation_layers": {
                            "scene_hypotheses": [
                                {
                                    "hypothesis_id": "scene.01",
                                    "label": "studio backing band with foreground vocal",
                                }
                            ],
                            "communicative_hypotheses": [
                                {
                                    "hypothesis_id": "comm.01",
                                    "label": "crowd echoes hook fragments",
                                }
                            ],
                            "separation_notes": {
                                "status": "query-conditioned",
                            },
                        },
                        "component_layers": {},
                        "transformation_intent": {
                            "operations": ["suppress", "retain", "summarize"],
                            "primary_output": "accompaniment_without_vocals",
                        },
                        "reconstruction": {
                            "reconstructable_outputs": ["accompaniment_without_vocals"],
                        },
                        "uncertainty_notes": {
                            "warnings": ["crowd interpretation remains low confidence"],
                        },
                        "provenance": {
                            "input_file_hash": "workspacehash",
                            "decode_backend": "wave",
                            "preprocessing_steps": ["decode", "observe"],
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(
                payload["attention_contract"],
                {
                    "query_text": "Keep accompaniment, suppress vocals, and summarize likely crowd interjections.",
                    "attention_targets": ["lead_vocal", "backing_band", "crowd_noise"],
                    "retain_targets": ["backing_band"],
                    "suppress_targets": ["lead_vocal"],
                    "answer_expectations": ["summarize crowd interjections"],
                    "render_goal": "instrumental bed with crowd-notes sidecar",
                },
            )
            self.assertEqual(
                payload["interpretation_layer_names"],
                ["communicative_hypotheses", "scene_hypotheses", "separation_notes"],
            )
            self.assertEqual(payload["interpretation_hypothesis_count"], 2)
            self.assertEqual(payload["first_scene_hypothesis"]["hypothesis_id"], "scene.01")
            self.assertEqual(payload["first_communicative_hypothesis"]["hypothesis_id"], "comm.01")
            self.assertEqual(
                payload["transformation_intent"],
                {
                    "operations": ["suppress", "retain", "summarize"],
                    "primary_output": "accompaniment_without_vocals",
                },
            )
            self.assertEqual(payload["reconstructable_outputs"], ["accompaniment_without_vocals"])

    def test_arwif_validate_analysis_reports_workspace_stats(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "validate-analysis.yaml"

            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "validate.demo-01",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/example.wav",
                            "duration_seconds": 8.0,
                            "sample_rate_hz": 16000,
                            "channel_count": 1,
                            "codec": "wav",
                        },
                        "attention_contract": {
                            "query_text": "keep accompaniment",
                            "retain_targets": ["backing_band"],
                        },
                        "observation_layers": {
                            "basic_observation_summary": {},
                            "onset_map": [],
                        },
                        "source_hypotheses": [],
                        "interpretation_layers": {
                            "scene_hypotheses": [
                                {
                                    "hypothesis_id": "scene.01",
                                    "label": "backing bed under vocal",
                                }
                            ]
                        },
                        "component_layers": {},
                        "transformation_intent": {
                            "operations": ["retain"],
                            "primary_output": "backing_band_only",
                        },
                        "reconstruction": {
                            "reconstructable_outputs": ["backing_band_only"],
                        },
                        "uncertainty_notes": {
                            "warnings": ["low confidence scene summary"],
                        },
                        "provenance": {
                            "decode_backend": "wave",
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-validate-analysis",
                str(analysis_document_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["analysis_document"], str(analysis_document_path))
            self.assertEqual(payload["stats"]["analysis_profile"], "basic-observation")
            self.assertEqual(payload["stats"]["source_id"], "validate.demo-01")
            self.assertEqual(payload["stats"]["observation_layer_count"], 2)
            self.assertEqual(payload["stats"]["reconstructable_output_count"], 1)
            self.assertEqual(payload["stats"]["uncertainty_warning_count"], 1)
            self.assertTrue(payload["stats"]["has_attention_contract"])
            self.assertTrue(payload["stats"]["has_interpretation_layers"])
            self.assertTrue(payload["stats"]["has_transformation_intent"])

    def test_arwif_inspect_analysis_rejects_invalid_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-analysis.json"
            analysis_document_path.write_text(
                json.dumps(
                    {
                        "analysis_metadata": [],
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    }
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("analysis_metadata", payload["errors"][0])

    def test_arwif_inspect_analysis_rejects_invalid_attention_contract_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-attention-contract.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.attention",
                        },
                        "observed_audio": {},
                        "attention_contract": {
                            "query_text": "keep the bed",
                            "attention_targets": "foreground_call_stream",
                        },
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("attention_contract.attention_targets", payload["errors"][0])

    def test_arwif_inspect_analysis_rejects_invalid_interpretation_layers_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-interpretation-layers.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.interpretation",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "interpretation_layers": {
                            "scene_hypotheses": ["foreground call over bed"],
                        },
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("interpretation_layers.scene_hypotheses[0]", payload["errors"][0])

    def test_arwif_inspect_analysis_rejects_invalid_transformation_intent_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-transformation-intent.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.transformation",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "transformation_intent": {
                            "operations": "suppress",
                        },
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("transformation_intent.operations", payload["errors"][0])

    def test_arwif_validate_analysis_rejects_invalid_attention_contract_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-validate-analysis.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.validate.analysis",
                        },
                        "observed_audio": {},
                        "attention_contract": {
                            "attention_targets": "foreground_call_stream",
                        },
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-validate-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("attention_contract.attention_targets", payload["errors"][0])

    def test_arwif_validate_analysis_rejects_invalid_source_hypothesis_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-source-hypothesis.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.source-hypothesis",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [
                            {
                                "source_id": "source.invalid.01",
                                "confidence": 1.2,
                                "linked_observations": {
                                    "section_indexes": [0],
                                },
                            }
                        ],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-validate-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("source_hypotheses[0].confidence", payload["errors"][0])

    def test_arwif_validate_analysis_rejects_invalid_observation_layer_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-observation-layers.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.observation-layers",
                        },
                        "observed_audio": {},
                        "observation_layers": {
                            "basic_observation_summary": {
                                "transition_motif_summary": {
                                    "recurring_motif_count": 1,
                                    "motif_occurrence_count": 1,
                                    "motif_signature_counts": {"steady": 1},
                                    "motif_signatures": ["steady"],
                                    "motifs": [
                                        {
                                            "motif_id": "transition_motif.01",
                                            "signature": "steady",
                                            "section_transition_indexes": ["0"],
                                        }
                                    ],
                                }
                            }
                        },
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-validate-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn(
                "observation_layers.basic_observation_summary.transition_motif_summary.motifs[0].section_transition_indexes[0]",
                payload["errors"][0],
            )

    def test_arwif_inspect_analysis_rejects_invalid_provenance_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-provenance.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.provenance",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {
                            "input_file_hash": "hash-valid",
                            "decode_backend": "wave",
                            "preprocessing_steps": ["decode"],
                            "analysis_parameters": {
                                "start_seconds": -0.1,
                            },
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("provenance.analysis_parameters.start_seconds", payload["errors"][0])

    def test_arwif_inspect_analysis_rejects_invalid_component_layer_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-component-layers.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.component-layers",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {
                            "harmonic_component_groups": [
                                {
                                    "component_id": "",
                                }
                            ]
                        },
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-inspect-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("component_layers.harmonic_component_groups[0].component_id", payload["errors"][0])

    def test_arwif_validate_analysis_rejects_invalid_reconstruction_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            analysis_document_path = tmp_dir / "invalid-reconstruction.yaml"
            analysis_document_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "invalid.reconstruction",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {
                            "reconstructable_outputs": "vocals",
                        },
                        "uncertainty_notes": {},
                        "provenance": {},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-validate-analysis",
                str(analysis_document_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"])
            self.assertIn("reconstruction.reconstructable_outputs", payload["errors"][0])

    def test_arwif_batch_validate_analysis_aggregates_valid_and_invalid_documents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_path = tmp_dir / "valid-analysis.yaml"
            invalid_path = tmp_dir / "invalid-analysis.yaml"
            report_path = tmp_dir / "batch-validate-analysis-report.json"

            valid_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "batch.validate.01",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/example.wav",
                            "duration_seconds": 6.0,
                            "sample_rate_hz": 16000,
                            "channel_count": 1,
                            "codec": "wav",
                        },
                        "attention_contract": {
                            "retain_targets": ["backing_band"],
                        },
                        "observation_layers": {
                            "basic_observation_summary": {},
                            "onset_map": [],
                            "section_boundaries": [],
                        },
                        "source_hypotheses": [],
                        "interpretation_layers": {
                            "scene_hypotheses": [
                                {
                                    "hypothesis_id": "scene.01",
                                    "label": "backing bed under vocal",
                                }
                            ]
                        },
                        "component_layers": {},
                        "transformation_intent": {
                            "operations": ["retain"],
                        },
                        "reconstruction": {
                            "reconstructable_outputs": ["backing_band_only"],
                        },
                        "uncertainty_notes": {
                            "warnings": ["low confidence scene summary"],
                        },
                        "provenance": {
                            "decode_backend": "wave",
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            invalid_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "batch.validate.invalid",
                        },
                        "observed_audio": {},
                        "observation_layers": {},
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {},
                        "uncertainty_notes": {},
                        "provenance": {},
                        "transformation_intent": {
                            "operations": "retain",
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-batch-validate-analysis",
                str(valid_path),
                str(invalid_path),
                "--output",
                str(report_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"], payload)
            self.assertEqual(payload["analysis_documents_processed"], 2)
            self.assertEqual(payload["valid_count"], 1)
            self.assertEqual(payload["invalid_count"], 1)
            self.assertEqual(payload["analysis_profile_counts"], {"basic-observation": 1})
            self.assertEqual(payload["total_observation_layer_count"], 3)
            self.assertEqual(payload["total_reconstructable_output_count"], 1)
            self.assertEqual(payload["total_uncertainty_warning_count"], 1)
            self.assertEqual(payload["documents_with_attention_contract"], 1)
            self.assertEqual(payload["documents_with_interpretation_layers"], 1)
            self.assertEqual(payload["documents_with_transformation_intent"], 1)
            self.assertEqual(payload["report_format"], "json")
            self.assertTrue(report_path.exists())
            self.assertEqual(len(payload["results"]), 2)
            invalid_result = next(
                result for result in payload["results"] if result["analysis_document"] == str(invalid_path)
            )
            self.assertFalse(invalid_result["is_valid"])
            self.assertIn("transformation_intent.operations", invalid_result["errors"][0])

            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_report["analysis_documents_processed"], 2)
            self.assertEqual(persisted_report["invalid_count"], 1)

    def test_arwif_batch_inspect_analysis_aggregates_structural_counts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first-analysis.yaml"
            second_path = tmp_dir / "second-analysis.json"
            report_path = tmp_dir / "batch-inspect-analysis-report.json"

            first_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.first",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/first.wav",
                    "duration_seconds": 6.0,
                    "sample_rate_hz": 16000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 16000,
                    "original_channel_count": 1,
                    "analysis_window": {
                        "start_seconds": 0.0,
                        "duration_seconds": 6.0,
                    },
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.4,
                        "rms_amplitude": 0.1,
                        "estimated_onset_count": 4,
                        "section_boundary_count": 1,
                        "section_candidate_count": 2,
                        "section_transition_count": 1,
                        "section_profile_summary": {
                            "average_duration_seconds": 3.0,
                            "longest_duration_seconds": 4.0,
                            "energy_band_counts": {"low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 2},
                            "position_band_counts": {"middle": 1, "opening": 1},
                            "dominant_energy_band": "low",
                            "opening_energy_band": "low",
                            "closing_energy_band": "medium",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.25,
                            "largest_abs_energy_delta": 0.25,
                            "transition_kind_counts": {"energy_increase": 1},
                            "dominant_transition_kind": "energy_increase",
                            "opening_transition_kind": "energy_increase",
                            "closing_transition_kind": "energy_increase",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 0,
                            "sequence_occurrence_count": 0,
                            "sequence_signature_counts": {},
                            "sequence_signatures": [],
                            "dominant_sequence_signature": None,
                            "sequences": [],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 0,
                            "chain_occurrence_count": 0,
                            "chain_signature_counts": {},
                            "chain_signatures": [],
                            "dominant_chain_signature": None,
                            "chains": [],
                        },
                        "frame_count": 96000,
                        "spectral_extent_summary": {"low_hz": 80, "high_hz": 4000},
                        "channel_energy_summary": {"center_rms": 0.1},
                    },
                    "onset_map": [{"offset_seconds": 0.4, "strength": 0.12}],
                    "transient_events": [],
                    "section_boundaries": [{"offset_seconds": 2.0, "confidence": 0.3, "energy_transition": "rise"}],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 2.0, "duration_seconds": 2.0, "rms_amplitude": 0.08, "relative_energy": 0.8, "energy_band": "low", "duration_band": "medium", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 2.0, "end_seconds": 6.0, "duration_seconds": 4.0, "rms_amplitude": 0.12, "relative_energy": 1.05, "energy_band": "medium", "duration_band": "medium", "position_band": "middle"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 2.0, "from_energy_band": "low", "to_energy_band": "medium", "energy_delta": 0.25, "duration_delta_seconds": 2.0, "transition_kind": "energy_increase"},
                    ],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {
                    "input_file_hash": "hash-first",
                    "decode_backend": "wave",
                    "preprocessing_steps": ["decode", "observe"],
                },
            }
            second_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.second",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/second.mp3",
                    "duration_seconds": 4.0,
                    "sample_rate_hz": 44100,
                    "channel_count": 2,
                    "codec": "mp3",
                    "original_sample_rate_hz": 44100,
                    "original_channel_count": 2,
                    "analysis_window": {
                        "start_seconds": 0.0,
                        "duration_seconds": 4.0,
                    },
                },
                "attention_contract": {
                    "query_text": "Keep the band, suppress the lead vocal, and summarize the foreground call stream.",
                    "attention_targets": ["foreground_call_stream", "band_bed"],
                    "retain_targets": ["band_bed"],
                    "suppress_targets": ["foreground_call_stream"],
                    "answer_expectations": ["summarize foreground call stream"],
                    "render_goal": "band bed without foreground call stream",
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.7,
                        "rms_amplitude": 0.2,
                        "estimated_onset_count": 6,
                        "section_boundary_count": 2,
                        "section_candidate_count": 3,
                        "section_transition_count": 2,
                        "section_profile_summary": {
                            "average_duration_seconds": 1.333333,
                            "longest_duration_seconds": 2.0,
                            "energy_band_counts": {"high": 1, "low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 1, "short": 2},
                            "position_band_counts": {"closing": 1, "middle": 1, "opening": 1},
                            "dominant_energy_band": "high",
                            "opening_energy_band": "medium",
                            "closing_energy_band": "high",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.18,
                            "largest_abs_energy_delta": 0.2,
                            "transition_kind_counts": {"energy_decrease": 1, "energy_stable": 1},
                            "dominant_transition_kind": "energy_decrease",
                            "opening_transition_kind": "energy_stable",
                            "closing_transition_kind": "energy_decrease",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 1,
                            "motif_occurrence_count": 2,
                            "motif_signature_counts": {"energy_stable|medium|low|stable": 2},
                            "motif_signatures": ["energy_stable|medium|low|stable"],
                            "dominant_motif_signature": "energy_stable|medium|low|stable",
                            "motifs": [
                                {
                                    "motif_id": "transition_motif.01",
                                    "signature": "energy_stable|medium|low|stable",
                                    "transition_kind": "energy_stable",
                                    "from_energy_band": "medium",
                                    "to_energy_band": "low",
                                    "duration_trend": "stable",
                                    "occurrence_count": 2,
                                    "section_transition_indexes": [0, 1],
                                    "boundary_offsets_seconds": [1.0, 2.0],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 1,
                            "sequence_occurrence_count": 2,
                            "sequence_signature_counts": {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
                            "sequence_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                            "dominant_sequence_signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                            "sequences": [
                                {
                                    "sequence_id": "transition_motif_sequence.01",
                                    "signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                                    "left_signature": "energy_stable|medium|low|stable",
                                    "right_signature": "energy_stable|medium|low|stable",
                                    "occurrence_count": 2,
                                    "section_transition_index_pairs": [[0, 1], [1, 2]],
                                    "boundary_offset_pairs_seconds": [[1.0, 2.0], [2.0, 3.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 1,
                            "chain_occurrence_count": 2,
                            "chain_signature_counts": {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
                            "chain_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                            "dominant_chain_signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                            "chains": [
                                {
                                    "chain_id": "transition_motif_chain.01",
                                    "signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                                    "motif_signatures": ["energy_stable|medium|low|stable", "energy_stable|medium|low|stable", "energy_stable|medium|low|stable"],
                                    "chain_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_chains": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_chains_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
                            "phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                            "dominant_phrase_signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable",
                                    "motif_signatures": ["energy_stable|medium|low|stable", "energy_stable|medium|low|stable", "energy_stable|medium|low|stable"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_family_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_family_count": 1,
                            "family_occurrence_count": 2,
                            "family_signature_counts": {"energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable": 2},
                            "family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"],
                            "dominant_family_signature": "energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable",
                            "families": [
                                {
                                    "family_id": "transition_motif_phrase_family.01",
                                    "signature": "energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable",
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_archetype_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_archetype_count": 1,
                            "archetype_occurrence_count": 2,
                            "archetype_signature_counts": {"energy_increase|rise_band|lengthen": 2},
                            "archetype_signatures": ["energy_increase|rise_band|lengthen"],
                            "dominant_archetype_signature": "energy_increase|rise_band|lengthen",
                            "archetypes": [
                                {
                                    "archetype_id": "transition_motif_phrase_archetype.01",
                                    "signature": "energy_increase|rise_band|lengthen",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_archetype_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_archetype_count": 1,
                            "archetype_occurrence_count": 2,
                            "archetype_signature_counts": {"energy_stable|fall_band|stable": 2},
                            "archetype_signatures": ["energy_stable|fall_band|stable"],
                            "dominant_archetype_signature": "energy_stable|fall_band|stable",
                            "archetypes": [
                                {
                                    "archetype_id": "transition_motif_phrase_archetype.01",
                                    "signature": "energy_stable|fall_band|stable",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_stable|fall_band": 2},
                            "contour_signatures": ["energy_stable|fall_band"],
                            "dominant_contour_signature": "energy_stable|fall_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_stable|fall_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_stable|fall_band|stable"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_sweep_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_sweep_count": 1,
                            "sweep_occurrence_count": 2,
                            "sweep_signature_counts": {"fall_band": 2},
                            "sweep_signatures": ["fall_band"],
                            "dominant_sweep_signature": "fall_band",
                            "sweeps": [
                                {
                                    "sweep_id": "transition_motif_phrase_sweep.01",
                                    "signature": "fall_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_stable|fall_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_stable|fall_band|stable"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "transition_motif_phrase_gesture_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_gesture_count": 1,
                            "gesture_occurrence_count": 2,
                            "gesture_signature_counts": {"single_direction_sweep": 2},
                            "gesture_signatures": ["single_direction_sweep"],
                            "dominant_gesture_signature": "single_direction_sweep",
                            "gestures": [
                                {
                                    "gesture_id": "transition_motif_phrase_gesture.01",
                                    "signature": "single_direction_sweep",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["rise_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_mobility_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_mobility_count": 1,
                            "mobility_occurrence_count": 2,
                            "mobility_signature_counts": {"traveling_band_region": 2},
                            "mobility_signatures": ["traveling_band_region"],
                            "dominant_mobility_signature": "traveling_band_region",
                            "mobilities": [
                                {
                                    "mobility_id": "transition_motif_phrase_mobility.01",
                                    "signature": "traveling_band_region",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_gesture_count": 1,
                                    "member_gesture_ids": ["transition_motif_phrase_gesture.01"],
                                    "member_gesture_signatures": ["single_direction_sweep"],
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["rise_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_gesture_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_gesture_count": 1,
                            "gesture_occurrence_count": 2,
                            "gesture_signature_counts": {"single_direction_sweep": 2},
                            "gesture_signatures": ["single_direction_sweep"],
                            "dominant_gesture_signature": "single_direction_sweep",
                            "gestures": [
                                {
                                    "gesture_id": "transition_motif_phrase_gesture.01",
                                    "signature": "single_direction_sweep",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["fall_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_stable|fall_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_stable|fall_band|stable"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.0, "duration_seconds": 4.0},
                                }
                            ],
                        },
                        "frame_count": 176400,
                        "spectral_extent_summary": {"low_hz": 60, "high_hz": 7200},
                        "channel_energy_summary": {"left_rms": 0.21, "right_rms": 0.19},
                    },
                    "onset_map": [{"offset_seconds": 0.2, "strength": 0.2}, {"offset_seconds": 1.2, "strength": 0.15}],
                    "transient_events": [],
                    "section_boundaries": [
                        {"offset_seconds": 1.0, "confidence": 0.2, "energy_transition": "rise"},
                        {"offset_seconds": 2.0, "confidence": 0.15, "energy_transition": "fall"},
                    ],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 1.0, "duration_seconds": 1.0, "rms_amplitude": 0.18, "relative_energy": 1.0, "energy_band": "medium", "duration_band": "short", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 1.0, "end_seconds": 2.0, "duration_seconds": 1.0, "rms_amplitude": 0.17, "relative_energy": 0.95, "energy_band": "low", "duration_band": "short", "position_band": "middle"},
                        {"section_index": 2, "start_seconds": 2.0, "end_seconds": 4.0, "duration_seconds": 2.0, "rms_amplitude": 0.24, "relative_energy": 1.2, "energy_band": "high", "duration_band": "medium", "position_band": "closing"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 1.0, "from_energy_band": "medium", "to_energy_band": "low", "energy_delta": -0.05, "duration_delta_seconds": 0.0, "transition_kind": "energy_stable"},
                        {"from_section_index": 1, "to_section_index": 2, "boundary_offset_seconds": 2.0, "from_energy_band": "low", "to_energy_band": "high", "energy_delta": 0.25, "duration_delta_seconds": 1.0, "transition_kind": "energy_decrease"},
                    ],
                },
                "source_hypotheses": [{"source_id": "source.vocal.01", "source_class": "foreground_call_stream", "role": "foreground_stream", "linked_observations": {"transition_motif_signatures": ["energy_stable|medium|low|stable"], "transition_motif_sequence_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable"], "transition_motif_chain_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"], "transition_motif_phrase_signatures": ["energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable"], "transition_motif_phrase_family_signatures": ["energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable"], "transition_motif_phrase_archetype_signatures": ["energy_stable|fall_band|stable"], "transition_motif_phrase_contour_signatures": ["energy_stable|fall_band"], "transition_motif_phrase_sweep_signatures": ["fall_band"], "transition_motif_phrase_gesture_signatures": ["single_direction_sweep"], "transition_motif_phrase_mobility_signatures": ["traveling_band_region"]}}],
                "interpretation_layers": {
                    "scene_hypotheses": [
                        {
                            "hypothesis_id": "scene.01",
                            "label": "foreground call over stereo band bed",
                        }
                    ],
                    "communicative_hypotheses": [
                        {
                            "hypothesis_id": "comm.01",
                            "label": "foreground call behaves like a query target",
                        }
                    ],
                    "separation_notes": {
                        "status": "task-conditioned",
                    },
                },
                "component_layers": {"harmonic_component_groups": [{"component_id": "component.01"}]},
                "transformation_intent": {
                    "operations": ["retain", "suppress", "summarize"],
                    "primary_output": "band_bed_without_foreground_call_stream",
                },
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": ["lossy source"]},
                "provenance": {
                    "input_file_hash": "hash-second",
                    "decode_backend": "ffmpeg",
                    "preprocessing_steps": ["decode", "observe", "window"],
                },
            }

            first_path.write_text(yaml.safe_dump(first_document, sort_keys=False), encoding="utf-8")
            second_path.write_text(json.dumps(second_document, indent=2), encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "arwif-batch-inspect-analysis",
                str(first_path),
                str(second_path),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["analysis_documents_processed"], 2)
            self.assertEqual(payload["valid_count"], 2)
            self.assertEqual(payload["invalid_count"], 0)
            self.assertEqual(payload["analysis_profile_counts"], {"basic-observation": 2})
            self.assertEqual(payload["codec_counts"], {"mp3": 1, "wav": 1})
            self.assertEqual(payload["decode_backend_counts"], {"ffmpeg": 1, "wave": 1})
            self.assertEqual(payload["documents_with_attention_contract"], 1)
            self.assertEqual(payload["documents_with_interpretation_layers"], 1)
            self.assertEqual(payload["documents_with_transformation_intent"], 1)
            self.assertEqual(payload["total_interpretation_hypothesis_count"], 2)
            self.assertEqual(
                payload["interpretation_layer_name_counts"],
                {
                    "communicative_hypotheses": 1,
                    "scene_hypotheses": 1,
                    "separation_notes": 1,
                },
            )
            self.assertEqual(payload["attention_target_counts"], {"band_bed": 1, "foreground_call_stream": 1})
            self.assertEqual(payload["retain_target_counts"], {"band_bed": 1})
            self.assertEqual(payload["suppress_target_counts"], {"foreground_call_stream": 1})
            self.assertEqual(payload["answer_expectation_counts"], {"summarize foreground call stream": 1})
            self.assertEqual(payload["render_goal_counts"], {"band bed without foreground call stream": 1})
            self.assertEqual(
                payload["transformation_operation_counts"],
                {"retain": 1, "summarize": 1, "suppress": 1},
            )
            self.assertEqual(
                payload["transformation_primary_output_counts"],
                {"band_bed_without_foreground_call_stream": 1},
            )
            self.assertEqual(payload["total_onset_map_count"], 3)
            self.assertEqual(payload["total_section_boundary_count"], 3)
            self.assertEqual(payload["total_section_candidate_count"], 5)
            self.assertEqual(payload["total_section_transition_count"], 3)
            self.assertEqual(payload["total_source_hypothesis_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_sequence_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_chain_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_family_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_archetype_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_contour_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_sweep_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_gesture_count"], 1)
            self.assertEqual(payload["total_recurring_transition_motif_phrase_mobility_count"], 1)
            self.assertEqual(
                payload["transition_motif_phrase_abstraction_totals"],
                {
                    "recurring_counts": {
                        "phrase": 1,
                        "family": 1,
                        "archetype": 1,
                        "contour": 1,
                        "sweep": 1,
                        "gesture": 1,
                        "mobility": 1,
                    },
                    "occurrence_counts": {
                        "phrase": 2,
                        "family": 2,
                        "archetype": 2,
                        "contour": 2,
                        "sweep": 2,
                        "gesture": 2,
                        "mobility": 2,
                    },
                },
            )
            self.assertEqual(
                payload["highest_stable_transition_motif_abstraction_layer_counts"],
                {
                    "mobility": 1,
                    "none": 1,
                },
            )
            self.assertEqual(
                payload["results"][0]["highest_stable_transition_motif_abstraction_layer"],
                {
                    "layer": "none",
                    "recurring_count": 0,
                    "occurrence_count": 0,
                },
            )
            self.assertEqual(
                payload["results"][1]["highest_stable_transition_motif_abstraction_layer"],
                {
                    "layer": "mobility",
                    "recurring_count": 1,
                    "occurrence_count": 2,
                },
            )
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_sequence_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_chain_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_family_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_archetype_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_contour_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_sweep_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_gesture_signature_count"], 1)
            self.assertEqual(payload["total_source_hypothesis_linked_transition_motif_phrase_mobility_signature_count"], 1)
            self.assertEqual(payload["source_hypothesis_class_counts"], {"foreground_call_stream": 1})
            self.assertEqual(payload["source_hypothesis_role_counts"], {"foreground_stream": 1})
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signature_counts"], {"energy_stable|medium|low|stable": 1})
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_sequence_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_chain_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_family_signature_counts"],
                {"energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_archetype_signature_counts"],
                {"energy_stable|fall_band|stable": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_contour_signature_counts"],
                {"energy_stable|fall_band": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_sweep_signature_counts"],
                {"fall_band": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_gesture_signature_counts"],
                {"single_direction_sweep": 1},
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_mobility_signature_counts"],
                {"traveling_band_region": 1},
            )
            self.assertEqual(payload["total_component_group_count"], 1)
            self.assertEqual(payload["total_uncertainty_warning_count"], 1)
            self.assertEqual(payload["dominant_section_energy_band_counts"], {"high": 1, "low": 1})
            self.assertEqual(payload["dominant_transition_kind_counts"], {"energy_decrease": 1, "energy_increase": 1})
            self.assertEqual(payload["dominant_transition_motif_signature_counts"], {"energy_stable|medium|low|stable": 1})
            self.assertEqual(
                payload["dominant_transition_motif_sequence_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_chain_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_family_signature_counts"],
                {"energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_archetype_signature_counts"],
                {"energy_stable|fall_band|stable": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_contour_signature_counts"],
                {"energy_stable|fall_band": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_sweep_signature_counts"],
                {"fall_band": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_gesture_signature_counts"],
                {"single_direction_sweep": 1},
            )
            self.assertEqual(
                payload["dominant_transition_motif_phrase_mobility_signature_counts"],
                {"traveling_band_region": 1},
            )
            self.assertEqual(payload["total_transition_kind_counts"], {"energy_decrease": 1, "energy_increase": 1, "energy_stable": 1})
            self.assertEqual(payload["transition_motif_signature_counts"], {"energy_stable|medium|low|stable": 2})
            self.assertEqual(
                payload["transition_motif_sequence_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
            )
            self.assertEqual(
                payload["transition_motif_chain_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_signature_counts"],
                {"energy_stable|medium|low|stable=>energy_stable|medium|low|stable=>energy_stable|medium|low|stable": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_family_signature_counts"],
                {"energy_stable|fall_band|stable=>energy_stable|fall_band|stable=>energy_stable|fall_band|stable": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_archetype_signature_counts"],
                {"energy_stable|fall_band|stable": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_contour_signature_counts"],
                {"energy_stable|fall_band": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_sweep_signature_counts"],
                {"fall_band": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_gesture_signature_counts"],
                {"single_direction_sweep": 2},
            )
            self.assertEqual(
                payload["transition_motif_phrase_mobility_signature_counts"],
                {"traveling_band_region": 2},
            )
            self.assertEqual(payload["report_format"], "json")
            self.assertTrue(report_path.exists())
            self.assertEqual(len(payload["results"]), 2)

    def test_arwif_batch_inspect_analysis_reports_invalid_documents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_path = tmp_dir / "valid-analysis.yaml"
            missing_path = tmp_dir / "missing-analysis.yaml"

            valid_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "demo.valid",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/valid.wav",
                            "duration_seconds": 1.0,
                            "sample_rate_hz": 8000,
                            "channel_count": 1,
                            "codec": "wav",
                            "original_sample_rate_hz": 8000,
                            "original_channel_count": 1,
                            "analysis_window": {"start_seconds": 0.0, "duration_seconds": 1.0},
                        },
                        "observation_layers": {
                            "basic_observation_summary": {
                                "peak_amplitude": 0.1,
                                "rms_amplitude": 0.05,
                                "estimated_onset_count": 0,
                                "section_boundary_count": 0,
                                "section_candidate_count": 0,
                                "section_transition_count": 0,
                                "section_profile_summary": {
                                    "average_duration_seconds": 0.0,
                                    "longest_duration_seconds": 0.0,
                                    "energy_band_counts": {},
                                    "duration_band_counts": {},
                                    "position_band_counts": {},
                                    "dominant_energy_band": None,
                                    "opening_energy_band": None,
                                    "closing_energy_band": None,
                                },
                                "transition_profile_summary": {
                                    "average_abs_energy_delta": 0.0,
                                    "largest_abs_energy_delta": 0.0,
                                    "transition_kind_counts": {},
                                    "dominant_transition_kind": None,
                                    "opening_transition_kind": None,
                                    "closing_transition_kind": None,
                                },
                                "frame_count": 8000,
                                "spectral_extent_summary": {"low_hz": 90, "high_hz": 1000},
                                "channel_energy_summary": {"center_rms": 0.05},
                            },
                            "onset_map": [],
                            "transient_events": [],
                            "section_boundaries": [],
                            "section_candidates": [],
                            "section_transitions": [],
                        },
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {"reconstructable_outputs": []},
                        "uncertainty_notes": {"warnings": []},
                        "provenance": {
                            "input_file_hash": "hash-valid",
                            "decode_backend": "wave",
                            "preprocessing_steps": ["decode", "observe"],
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-batch-inspect-analysis",
                str(valid_path),
                str(missing_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"], payload)
            self.assertEqual(payload["analysis_documents_processed"], 2)
            self.assertEqual(payload["valid_count"], 1)
            self.assertEqual(payload["invalid_count"], 1)
            invalid_result = next(result for result in payload["results"] if result["analysis_document"] == str(missing_path))
            self.assertFalse(invalid_result["is_valid"])
            self.assertIn("does not exist", invalid_result["errors"][0])

    def test_arwif_batch_diff_analysis_aggregates_recurring_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_changed_path = tmp_dir / "left-changed.yaml"
            right_changed_path = tmp_dir / "right-changed.yaml"
            left_same_path = tmp_dir / "left-same.yaml"
            right_same_path = tmp_dir / "right-same.yaml"
            report_path = tmp_dir / "batch-diff-analysis-report.yaml"

            left_changed_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.left.changed",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/left.wav",
                    "duration_seconds": 8.0,
                    "sample_rate_hz": 16000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 16000,
                    "original_channel_count": 1,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 8.0},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.4,
                        "rms_amplitude": 0.1,
                        "estimated_onset_count": 8,
                        "section_boundary_count": 1,
                        "section_candidate_count": 2,
                        "section_transition_count": 1,
                        "section_profile_summary": {
                            "average_duration_seconds": 4.0,
                            "longest_duration_seconds": 5.0,
                            "energy_band_counts": {"low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 2},
                            "position_band_counts": {"middle": 1, "opening": 1},
                            "dominant_energy_band": "low",
                            "opening_energy_band": "low",
                            "closing_energy_band": "medium",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.15,
                            "largest_abs_energy_delta": 0.15,
                            "transition_kind_counts": {"energy_stable": 1},
                            "dominant_transition_kind": "energy_stable",
                            "opening_transition_kind": "energy_stable",
                            "closing_transition_kind": "energy_stable",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "frame_count": 128000,
                        "spectral_extent_summary": {"low_hz": 80, "high_hz": 4200},
                        "channel_energy_summary": {"center_rms": 0.1},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_boundaries": [{"offset_seconds": 3.0, "confidence": 0.2, "energy_transition": "rise"}],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 3.0, "duration_seconds": 3.0, "rms_amplitude": 0.08, "relative_energy": 0.8, "energy_band": "low", "duration_band": "medium", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 3.0, "end_seconds": 8.0, "duration_seconds": 5.0, "rms_amplitude": 0.11, "relative_energy": 1.0, "energy_band": "medium", "duration_band": "medium", "position_band": "middle"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 3.0, "from_energy_band": "low", "to_energy_band": "medium", "energy_delta": 0.2, "duration_delta_seconds": 2.0, "transition_kind": "energy_stable"},
                    ],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {"input_file_hash": "hash-left", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
            }
            right_changed_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.right.changed",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/right.mp3",
                    "duration_seconds": 8.5,
                    "sample_rate_hz": 44100,
                    "channel_count": 2,
                    "codec": "mp3",
                    "original_sample_rate_hz": 44100,
                    "original_channel_count": 2,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 8.5},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.7,
                        "rms_amplitude": 0.2,
                        "estimated_onset_count": 10,
                        "section_boundary_count": 2,
                        "section_candidate_count": 3,
                        "section_transition_count": 2,
                        "section_profile_summary": {
                            "average_duration_seconds": 2.833333,
                            "longest_duration_seconds": 4.5,
                            "energy_band_counts": {"high": 1, "low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 2, "short": 1},
                            "position_band_counts": {"closing": 1, "middle": 1, "opening": 1},
                            "dominant_energy_band": "high",
                            "opening_energy_band": "medium",
                            "closing_energy_band": "high",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.25,
                            "largest_abs_energy_delta": 0.4,
                            "transition_kind_counts": {"energy_decrease": 1, "energy_increase": 1},
                            "dominant_transition_kind": "energy_decrease",
                            "opening_transition_kind": "energy_increase",
                            "closing_transition_kind": "energy_decrease",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 1,
                            "motif_occurrence_count": 2,
                            "motif_signature_counts": {"energy_increase|low|high|lengthen": 2},
                            "motif_signatures": ["energy_increase|low|high|lengthen"],
                            "dominant_motif_signature": "energy_increase|low|high|lengthen",
                            "motifs": [
                                {
                                    "motif_id": "transition_motif.01",
                                    "signature": "energy_increase|low|high|lengthen",
                                    "transition_kind": "energy_increase",
                                    "from_energy_band": "low",
                                    "to_energy_band": "high",
                                    "duration_trend": "lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_indexes": [0, 1],
                                    "boundary_offsets_seconds": [2.0, 4.0],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 1,
                            "sequence_occurrence_count": 2,
                            "sequence_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_sequence_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "sequences": [
                                {
                                    "sequence_id": "transition_motif_sequence.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "left_signature": "energy_increase|low|high|lengthen",
                                    "right_signature": "energy_increase|low|high|lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_index_pairs": [[0, 1], [1, 2]],
                                    "boundary_offset_pairs_seconds": [[2.0, 4.0], [4.0, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 1,
                            "chain_occurrence_count": 2,
                            "chain_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_chain_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "chains": [
                                {
                                    "chain_id": "transition_motif_chain.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "chain_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_chains": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_chains_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_family_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_family_count": 1,
                            "family_occurrence_count": 2,
                            "family_signature_counts": {"energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen": 2},
                            "family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                            "dominant_family_signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                            "families": [
                                {
                                    "family_id": "transition_motif_phrase_family.01",
                                    "signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_archetype_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_archetype_count": 1,
                            "archetype_occurrence_count": 2,
                            "archetype_signature_counts": {"energy_increase|rise_band|lengthen": 2},
                            "archetype_signatures": ["energy_increase|rise_band|lengthen"],
                            "dominant_archetype_signature": "energy_increase|rise_band|lengthen",
                            "archetypes": [
                                {
                                    "archetype_id": "transition_motif_phrase_archetype.01",
                                    "signature": "energy_increase|rise_band|lengthen",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_sweep_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_sweep_count": 1,
                            "sweep_occurrence_count": 2,
                            "sweep_signature_counts": {"rise_band": 2},
                            "sweep_signatures": ["rise_band"],
                            "dominant_sweep_signature": "rise_band",
                            "sweeps": [
                                {
                                    "sweep_id": "transition_motif_phrase_sweep.01",
                                    "signature": "rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_gesture_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_gesture_count": 1,
                            "gesture_occurrence_count": 2,
                            "gesture_signature_counts": {"single_direction_sweep": 2},
                            "gesture_signatures": ["single_direction_sweep"],
                            "dominant_gesture_signature": "single_direction_sweep",
                            "gestures": [
                                {
                                    "gesture_id": "transition_motif_phrase_gesture.01",
                                    "signature": "single_direction_sweep",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["rise_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[2.0, 4.0, 6.0], [4.0, 6.0, 8.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 8.5, "duration_seconds": 8.5},
                                }
                            ],
                        },
                        "frame_count": 374850,
                        "spectral_extent_summary": {"low_hz": 60, "high_hz": 7200},
                        "channel_energy_summary": {"left_rms": 0.21, "right_rms": 0.19},
                    },
                    "onset_map": [{"offset_seconds": 0.4, "strength": 0.2}],
                    "transient_events": [],
                    "section_boundaries": [
                        {"offset_seconds": 2.0, "confidence": 0.3, "energy_transition": "rise"},
                        {"offset_seconds": 4.0, "confidence": 0.25, "energy_transition": "fall"},
                    ],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 2.0, "duration_seconds": 2.0, "rms_amplitude": 0.18, "relative_energy": 1.0, "energy_band": "medium", "duration_band": "medium", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 2.0, "end_seconds": 4.0, "duration_seconds": 2.0, "rms_amplitude": 0.15, "relative_energy": 0.8, "energy_band": "low", "duration_band": "medium", "position_band": "middle"},
                        {"section_index": 2, "start_seconds": 4.0, "end_seconds": 8.5, "duration_seconds": 4.5, "rms_amplitude": 0.24, "relative_energy": 1.3, "energy_band": "high", "duration_band": "medium", "position_band": "closing"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 2.0, "from_energy_band": "medium", "to_energy_band": "low", "energy_delta": -0.2, "duration_delta_seconds": 0.0, "transition_kind": "energy_increase"},
                        {"from_section_index": 1, "to_section_index": 2, "boundary_offset_seconds": 4.0, "from_energy_band": "low", "to_energy_band": "high", "energy_delta": 0.5, "duration_delta_seconds": 2.5, "transition_kind": "energy_decrease"},
                    ],
                },
                "source_hypotheses": [{"source_id": "source.vocal.01", "source_class": "transient_event_cluster", "role": "event_layer", "linked_observations": {"transition_motif_signatures": ["energy_increase|low|high|lengthen"], "transition_motif_sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"], "transition_motif_phrase_archetype_signatures": ["energy_increase|rise_band|lengthen"], "transition_motif_phrase_contour_signatures": ["energy_increase|rise_band"], "transition_motif_phrase_sweep_signatures": ["rise_band"], "transition_motif_phrase_gesture_signatures": ["single_direction_sweep"]}}],
                "component_layers": {"harmonic_component_groups": [{"component_id": "component.01"}]},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": ["lossy source"]},
                "attention_contract": {
                    "query_text": "Which event layer should stay foregrounded?",
                    "attention_targets": ["event layer", "rising transition"],
                    "retain_targets": ["event layer"],
                    "suppress_targets": ["steady bed"],
                    "answer_expectations": ["identify the foregrounded event layer"],
                    "render_goal": "keep the event layer prominent",
                },
                "interpretation_layers": {
                    "scene_hypotheses": [
                        {
                            "hypothesis_id": "scene.changed.01",
                            "label": "event layer punctuates a rising backdrop",
                            "confidence": 0.34,
                            "confidence_band": "low",
                            "hypothesis_origin": "task_conditioned_initialization",
                            "observed_source_classes": ["transient_event_cluster"],
                            "linked_source_ids": ["source.vocal.01"],
                            "attention_targets_matched_source_classes": ["transient_event_cluster"],
                            "attention_targets_unmatched": ["rising transition"],
                        }
                    ],
                    "communicative_hypotheses": [
                        {
                            "hypothesis_id": "communicative.changed.01",
                            "label": "event layer is the likely answer-bearing stream",
                            "confidence": 0.29,
                            "confidence_band": "low",
                            "hypothesis_origin": "task_conditioned_initialization",
                            "linked_source_classes": ["transient_event_cluster"],
                            "answer_expectations": ["identify the foregrounded event layer"],
                        }
                    ],
                    "task_conditioning_notes": [
                        {
                            "note_id": "task-note.changed.01",
                            "kind": "attention_bias",
                            "text": "Prefer event-layer explanations over static bed descriptions.",
                        }
                    ],
                },
                "transformation_intent": {
                    "operations": ["retain_foreground", "reduce_bed"],
                    "primary_output": "event_layer_stem",
                },
                "provenance": {"input_file_hash": "hash-right", "decode_backend": "ffmpeg", "preprocessing_steps": ["decode", "observe", "window"]},
            }

            unchanged_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.same",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/same.wav",
                    "duration_seconds": 3.0,
                    "sample_rate_hz": 8000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 8000,
                    "original_channel_count": 1,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 3.0},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.2,
                        "rms_amplitude": 0.05,
                        "estimated_onset_count": 2,
                        "section_boundary_count": 0,
                        "section_candidate_count": 0,
                        "section_transition_count": 0,
                        "section_profile_summary": {
                            "average_duration_seconds": 0.0,
                            "longest_duration_seconds": 0.0,
                            "energy_band_counts": {},
                            "duration_band_counts": {},
                            "position_band_counts": {},
                            "dominant_energy_band": None,
                            "opening_energy_band": None,
                            "closing_energy_band": None,
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.0,
                            "largest_abs_energy_delta": 0.0,
                            "transition_kind_counts": {},
                            "dominant_transition_kind": None,
                            "opening_transition_kind": None,
                            "closing_transition_kind": None,
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 0,
                            "sequence_occurrence_count": 0,
                            "sequence_signature_counts": {},
                            "sequence_signatures": [],
                            "dominant_sequence_signature": None,
                            "sequences": [],
                        },
                        "frame_count": 24000,
                        "spectral_extent_summary": {"low_hz": 90, "high_hz": 1000},
                        "channel_energy_summary": {"center_rms": 0.05},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_boundaries": [],
                    "section_candidates": [],
                    "section_transitions": [],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {"input_file_hash": "hash-same", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
            }

            left_changed_path.write_text(yaml.safe_dump(left_changed_document, sort_keys=False), encoding="utf-8")
            right_changed_path.write_text(yaml.safe_dump(right_changed_document, sort_keys=False), encoding="utf-8")
            serialized_same = yaml.safe_dump(unchanged_document, sort_keys=False)
            left_same_path.write_text(serialized_same, encoding="utf-8")
            right_same_path.write_text(serialized_same, encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "arwif-batch-diff-analysis",
                "--left",
                str(left_changed_path),
                str(left_same_path),
                "--right",
                str(right_changed_path),
                str(right_same_path),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 2)
            self.assertEqual(payload["changed_pairs"], 1)
            self.assertEqual(payload["unchanged_pairs"], 1)
            self.assertEqual(payload["invalid_pairs"], 0)
            self.assertEqual(payload["report_format"], "yaml")
            self.assertTrue(report_path.exists())
            self.assertEqual(payload["metadata_fields_changed_in_all_changed_pairs"], ["source_id"])
            self.assertIn("codec", payload["observed_audio_fields_changed_in_all_changed_pairs"])
            self.assertEqual(
                payload["attention_contract_fields_changed_in_all_changed_pairs"],
                [
                    "answer_expectations",
                    "attention_targets",
                    "query_text",
                    "render_goal",
                    "retain_targets",
                    "suppress_targets",
                ],
            )
            self.assertEqual(
                payload["transformation_intent_fields_changed_in_all_changed_pairs"],
                ["operations", "primary_output"],
            )
            self.assertEqual(
                payload["interpretation_layers_added_in_all_changed_pairs"],
                ["communicative_hypotheses", "scene_hypotheses", "task_conditioning_notes"],
            )
            self.assertIn("section_profile_summary.dominant_energy_band", payload["basic_observation_fields_changed_in_all_changed_pairs"])
            self.assertIn("transition_profile_summary.dominant_transition_kind", payload["basic_observation_fields_changed_in_all_changed_pairs"])
            self.assertIn("transition_motif_summary.dominant_motif_signature", payload["basic_observation_fields_changed_in_all_changed_pairs"])
            self.assertIn(
                "transition_motif_phrase_abstraction_ladder.recurring_counts.phrase",
                payload["basic_observation_fields_changed_in_all_changed_pairs"],
            )
            self.assertIn(
                "transition_motif_sequence_summary.dominant_sequence_signature",
                payload["basic_observation_fields_changed_in_all_changed_pairs"],
            )
            self.assertEqual(payload["source_hypothesis_classes_added_in_all_changed_pairs"], ["transient_event_cluster"])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signatures_added_in_all_changed_pairs"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_sequence_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_chain_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
                ["single_direction_sweep"],
            )
            self.assertEqual(payload["transition_motif_signatures_added_in_all_changed_pairs"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["transition_motif_sequence_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_chain_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
                ["single_direction_sweep"],
            )
            self.assertEqual(payload["source_hypothesis_classes_added_frequencies"][0]["source_hypothesis_class"], "transient_event_cluster")
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signatures_added_frequencies"][0]["transition_motif_signature"], "energy_increase|low|high|lengthen")
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_sequence_signatures_added_frequencies"][0]["transition_motif_sequence_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_chain_signatures_added_frequencies"][0]["transition_motif_chain_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_signatures_added_frequencies"][0]["transition_motif_phrase_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_added_frequencies"][0]["transition_motif_phrase_family_signature"],
                "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_frequencies"][0]["transition_motif_phrase_archetype_signature"],
                "energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_frequencies"][0]["transition_motif_phrase_contour_signature"],
                "energy_increase|rise_band",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_frequencies"][0]["transition_motif_phrase_sweep_signature"],
                "rise_band",
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_frequencies"][0]["transition_motif_phrase_gesture_signature"],
                "single_direction_sweep",
            )
            self.assertEqual(payload["transition_motif_signatures_added_frequencies"][0]["transition_motif_signature"], "energy_increase|low|high|lengthen")
            self.assertEqual(
                payload["transition_motif_sequence_signatures_added_frequencies"][0]["transition_motif_sequence_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["transition_motif_chain_signatures_added_frequencies"][0]["transition_motif_chain_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["transition_motif_phrase_signatures_added_frequencies"][0]["transition_motif_phrase_signature"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["transition_motif_phrase_family_signatures_added_frequencies"][0]["transition_motif_phrase_family_signature"],
                "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["transition_motif_phrase_archetype_signatures_added_frequencies"][0]["transition_motif_phrase_archetype_signature"],
                "energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["transition_motif_phrase_contour_signatures_added_frequencies"][0]["transition_motif_phrase_contour_signature"],
                "energy_increase|rise_band",
            )
            self.assertEqual(
                payload["transition_motif_phrase_sweep_signatures_added_frequencies"][0]["transition_motif_phrase_sweep_signature"],
                "rise_band",
            )
            self.assertEqual(
                payload["transition_motif_phrase_gesture_signatures_added_frequencies"][0]["transition_motif_phrase_gesture_signature"],
                "single_direction_sweep",
            )
            self.assertEqual(payload["attention_contract_field_frequencies"][0]["field"], "answer_expectations")
            self.assertEqual(payload["attention_contract_field_frequencies"][0]["pairs_changed"], 1)
            self.assertEqual(payload["transformation_intent_field_frequencies"][0]["field"], "operations")
            self.assertEqual(payload["interpretation_layers_added_frequencies"][0]["layer"], "communicative_hypotheses")
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_section_candidate_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_section_candidate_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_section_transition_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_section_transition_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_interpretation_hypothesis_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_interpretation_hypothesis_count_delta"], 3)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_sequence_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_sequence_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_chain_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_chain_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_family_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_family_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_archetype_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_archetype_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_contour_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_contour_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_sweep_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_sweep_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_recurring_transition_motif_phrase_gesture_count_delta"], 1)
            self.assertEqual(payload["analysis_change_summary"]["total_recurring_transition_motif_phrase_gesture_count_delta"], 1)
            self.assertEqual(
                payload["analysis_change_summary"]["pairs_with_highest_stable_transition_motif_abstraction_layer_change"],
                1,
            )
            self.assertEqual(
                payload["analysis_change_summary"]["pairs_with_highest_stable_transition_motif_abstraction_layer_rise"],
                1,
            )
            self.assertEqual(
                payload["analysis_change_summary"]["pairs_with_highest_stable_transition_motif_abstraction_layer_fall"],
                0,
            )
            self.assertEqual(
                payload["analysis_change_summary"]["total_highest_stable_transition_motif_abstraction_layer_step_delta"],
                9,
            )
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_first_scene_hypothesis_change"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_first_communicative_hypothesis_change"], 1)
            self.assertEqual(payload["analysis_change_summary"]["pairs_with_transformation_intent_change"], 1)
            self.assertEqual(
                payload["results"][0]["highest_stable_transition_motif_abstraction_layer_change"]["direction"],
                "rose",
            )
            self.assertEqual(payload["results"][0]["pair_index"], 0)
            self.assertTrue(payload["results"][0]["pair_changed"])
            self.assertFalse(payload["results"][1]["pair_changed"])

    def test_arwif_batch_diff_analysis_reports_invalid_documents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_path = tmp_dir / "valid-analysis.yaml"
            missing_path = tmp_dir / "missing-analysis.yaml"

            valid_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "demo.valid",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/valid.wav",
                            "duration_seconds": 1.0,
                            "sample_rate_hz": 8000,
                            "channel_count": 1,
                            "codec": "wav",
                            "original_sample_rate_hz": 8000,
                            "original_channel_count": 1,
                            "analysis_window": {"start_seconds": 0.0, "duration_seconds": 1.0},
                        },
                        "observation_layers": {
                            "basic_observation_summary": {
                                "peak_amplitude": 0.1,
                                "rms_amplitude": 0.05,
                                "estimated_onset_count": 0,
                                "section_boundary_count": 0,
                                "section_candidate_count": 0,
                                "section_transition_count": 0,
                                "section_profile_summary": {
                                    "average_duration_seconds": 0.0,
                                    "longest_duration_seconds": 0.0,
                                    "energy_band_counts": {},
                                    "duration_band_counts": {},
                                    "position_band_counts": {},
                                    "dominant_energy_band": None,
                                    "opening_energy_band": None,
                                    "closing_energy_band": None,
                                },
                                "transition_profile_summary": {
                                    "average_abs_energy_delta": 0.0,
                                    "largest_abs_energy_delta": 0.0,
                                    "transition_kind_counts": {},
                                    "dominant_transition_kind": None,
                                    "opening_transition_kind": None,
                                    "closing_transition_kind": None,
                                },
                                "frame_count": 8000,
                                "spectral_extent_summary": {"low_hz": 90, "high_hz": 1000},
                                "channel_energy_summary": {"center_rms": 0.05},
                            },
                            "onset_map": [],
                            "transient_events": [],
                            "section_boundaries": [],
                            "section_candidates": [],
                            "section_transitions": [],
                        },
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {"reconstructable_outputs": []},
                        "uncertainty_notes": {"warnings": []},
                        "provenance": {"input_file_hash": "hash-valid", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-batch-diff-analysis",
                "--left",
                str(valid_path),
                str(valid_path),
                "--right",
                str(valid_path),
                str(missing_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 2)
            self.assertEqual(payload["changed_pairs"], 0)
            self.assertEqual(payload["unchanged_pairs"], 2)
            self.assertEqual(payload["invalid_pairs"], 1)
            invalid_result = next(result for result in payload["results"] if result["right"] == str(missing_path))
            self.assertFalse(invalid_result["left_valid"])
            self.assertFalse(invalid_result["right_valid"])
            self.assertIn("does not exist", invalid_result["errors"][0])

    def test_arwif_batch_review_analysis_runs_diff_and_review_together(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_changed_path = tmp_dir / "left-changed.yaml"
            right_changed_path = tmp_dir / "right-changed.yaml"
            left_same_path = tmp_dir / "left-same.yaml"
            right_same_path = tmp_dir / "right-same.yaml"
            review_report_path = tmp_dir / "batch-review-analysis-report.json"

            changed_left_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.left.review",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/review-left.wav",
                    "duration_seconds": 6.0,
                    "sample_rate_hz": 16000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 16000,
                    "original_channel_count": 1,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 6.0},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.35,
                        "rms_amplitude": 0.09,
                        "estimated_onset_count": 4,
                        "section_boundary_count": 1,
                        "section_candidate_count": 2,
                        "section_transition_count": 1,
                        "section_profile_summary": {
                            "average_duration_seconds": 3.0,
                            "longest_duration_seconds": 4.0,
                            "energy_band_counts": {"low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 2},
                            "position_band_counts": {"opening": 1, "middle": 1},
                            "dominant_energy_band": "low",
                            "opening_energy_band": "low",
                            "closing_energy_band": "medium",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.12,
                            "largest_abs_energy_delta": 0.12,
                            "transition_kind_counts": {"energy_stable": 1},
                            "dominant_transition_kind": "energy_stable",
                            "opening_transition_kind": "energy_stable",
                            "closing_transition_kind": "energy_stable",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 0,
                            "sequence_occurrence_count": 0,
                            "sequence_signature_counts": {},
                            "sequence_signatures": [],
                            "dominant_sequence_signature": None,
                            "sequences": [],
                        },
                        "frame_count": 96000,
                        "spectral_extent_summary": {"low_hz": 70, "high_hz": 3500},
                        "channel_energy_summary": {"center_rms": 0.09},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_boundaries": [{"offset_seconds": 2.0, "confidence": 0.2, "energy_transition": "rise"}],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 2.0, "duration_seconds": 2.0, "rms_amplitude": 0.07, "relative_energy": 0.8, "energy_band": "low", "duration_band": "medium", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 2.0, "end_seconds": 6.0, "duration_seconds": 4.0, "rms_amplitude": 0.11, "relative_energy": 1.1, "energy_band": "medium", "duration_band": "medium", "position_band": "middle"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 2.0, "from_energy_band": "low", "to_energy_band": "medium", "energy_delta": 0.3, "duration_delta_seconds": 2.0, "transition_kind": "energy_stable"},
                    ],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {"input_file_hash": "hash-review-left", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
            }
            changed_right_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.right.review",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/review-right.mp3",
                    "duration_seconds": 6.5,
                    "sample_rate_hz": 44100,
                    "channel_count": 2,
                    "codec": "mp3",
                    "original_sample_rate_hz": 44100,
                    "original_channel_count": 2,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 6.5},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.62,
                        "rms_amplitude": 0.19,
                        "estimated_onset_count": 7,
                        "section_boundary_count": 2,
                        "section_candidate_count": 3,
                        "section_transition_count": 2,
                        "section_profile_summary": {
                            "average_duration_seconds": 2.166667,
                            "longest_duration_seconds": 3.0,
                            "energy_band_counts": {"high": 1, "low": 1, "medium": 1},
                            "duration_band_counts": {"medium": 1, "short": 2},
                            "position_band_counts": {"opening": 1, "middle": 1, "closing": 1},
                            "dominant_energy_band": "high",
                            "opening_energy_band": "medium",
                            "closing_energy_band": "high",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.26,
                            "largest_abs_energy_delta": 0.4,
                            "transition_kind_counts": {"energy_decrease": 1, "energy_increase": 1},
                            "dominant_transition_kind": "energy_decrease",
                            "opening_transition_kind": "energy_increase",
                            "closing_transition_kind": "energy_decrease",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 1,
                            "motif_occurrence_count": 2,
                            "motif_signature_counts": {"energy_increase|low|high|lengthen": 2},
                            "motif_signatures": ["energy_increase|low|high|lengthen"],
                            "dominant_motif_signature": "energy_increase|low|high|lengthen",
                            "motifs": [
                                {
                                    "motif_id": "transition_motif.01",
                                    "signature": "energy_increase|low|high|lengthen",
                                    "transition_kind": "energy_increase",
                                    "from_energy_band": "low",
                                    "to_energy_band": "high",
                                    "duration_trend": "lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_indexes": [0, 1],
                                    "boundary_offsets_seconds": [1.5, 3.5],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 1,
                            "sequence_occurrence_count": 2,
                            "sequence_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_sequence_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "sequences": [
                                {
                                    "sequence_id": "transition_motif_sequence.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "left_signature": "energy_increase|low|high|lengthen",
                                    "right_signature": "energy_increase|low|high|lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_index_pairs": [[0, 1], [1, 2]],
                                    "boundary_offset_pairs_seconds": [[1.5, 3.5], [3.5, 5.5]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 1,
                            "chain_occurrence_count": 2,
                            "chain_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_chain_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "chains": [
                                {
                                    "chain_id": "transition_motif_chain.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "chain_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_chains": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_chains_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_family_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_family_count": 1,
                            "family_occurrence_count": 2,
                            "family_signature_counts": {"energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen": 2},
                            "family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                            "dominant_family_signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                            "families": [
                                {
                                    "family_id": "transition_motif_phrase_family.01",
                                    "signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_archetype_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_archetype_count": 1,
                            "archetype_occurrence_count": 2,
                            "archetype_signature_counts": {"energy_increase|rise_band|lengthen": 2},
                            "archetype_signatures": ["energy_increase|rise_band|lengthen"],
                            "dominant_archetype_signature": "energy_increase|rise_band|lengthen",
                            "archetypes": [
                                {
                                    "archetype_id": "transition_motif_phrase_archetype.01",
                                    "signature": "energy_increase|rise_band|lengthen",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_sweep_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_sweep_count": 1,
                            "sweep_occurrence_count": 2,
                            "sweep_signature_counts": {"rise_band": 2},
                            "sweep_signatures": ["rise_band"],
                            "dominant_sweep_signature": "rise_band",
                            "sweeps": [
                                {
                                    "sweep_id": "transition_motif_phrase_sweep.01",
                                    "signature": "rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_gesture_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_gesture_count": 1,
                            "gesture_occurrence_count": 2,
                            "gesture_signature_counts": {"single_direction_sweep": 2},
                            "gesture_signatures": ["single_direction_sweep"],
                            "dominant_gesture_signature": "single_direction_sweep",
                            "gestures": [
                                {
                                    "gesture_id": "transition_motif_phrase_gesture.01",
                                    "signature": "single_direction_sweep",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["rise_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[1, 2, 3], [2, 3, 4]],
                                    "boundary_offset_phrases_seconds": [[1.5, 3.5, 5.5], [3.5, 5.5, 6.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 6.5, "duration_seconds": 6.5},
                                }
                            ],
                        },
                        "frame_count": 286650,
                        "spectral_extent_summary": {"low_hz": 55, "high_hz": 7600},
                        "channel_energy_summary": {"left_rms": 0.2, "right_rms": 0.18},
                    },
                    "onset_map": [{"offset_seconds": 0.5, "strength": 0.18}],
                    "transient_events": [],
                    "section_boundaries": [
                        {"offset_seconds": 1.5, "confidence": 0.22, "energy_transition": "rise"},
                        {"offset_seconds": 3.5, "confidence": 0.2, "energy_transition": "fall"},
                    ],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 1.5, "duration_seconds": 1.5, "rms_amplitude": 0.16, "relative_energy": 1.0, "energy_band": "medium", "duration_band": "short", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 1.5, "end_seconds": 3.5, "duration_seconds": 2.0, "rms_amplitude": 0.12, "relative_energy": 0.75, "energy_band": "low", "duration_band": "medium", "position_band": "middle"},
                        {"section_index": 2, "start_seconds": 3.5, "end_seconds": 6.5, "duration_seconds": 3.0, "rms_amplitude": 0.24, "relative_energy": 1.3, "energy_band": "high", "duration_band": "medium", "position_band": "closing"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 1.5, "from_energy_band": "medium", "to_energy_band": "low", "energy_delta": -0.25, "duration_delta_seconds": 0.5, "transition_kind": "energy_increase"},
                        {"from_section_index": 1, "to_section_index": 2, "boundary_offset_seconds": 3.5, "from_energy_band": "low", "to_energy_band": "high", "energy_delta": 0.55, "duration_delta_seconds": 1.0, "transition_kind": "energy_decrease"},
                    ],
                },
                "source_hypotheses": [{"source_id": "source.review.01", "linked_observations": {"transition_motif_signatures": ["energy_increase|low|high|lengthen"], "transition_motif_sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"], "transition_motif_phrase_archetype_signatures": ["energy_increase|rise_band|lengthen"], "transition_motif_phrase_contour_signatures": ["energy_increase|rise_band"], "transition_motif_phrase_sweep_signatures": ["rise_band"], "transition_motif_phrase_gesture_signatures": ["single_direction_sweep"]}}],
                "component_layers": {"harmonic_component_groups": [{"component_id": "component.review.01"}]},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": ["lossy source"]},
                "provenance": {"input_file_hash": "hash-review-right", "decode_backend": "ffmpeg", "preprocessing_steps": ["decode", "observe", "window"]},
            }

            unchanged_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.same.review",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/review-same.wav",
                    "duration_seconds": 2.0,
                    "sample_rate_hz": 8000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 8000,
                    "original_channel_count": 1,
                    "analysis_window": {"start_seconds": 0.0, "duration_seconds": 2.0},
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.2,
                        "rms_amplitude": 0.05,
                        "estimated_onset_count": 1,
                        "section_boundary_count": 0,
                        "section_candidate_count": 0,
                        "section_transition_count": 0,
                        "section_profile_summary": {
                            "average_duration_seconds": 0.0,
                            "longest_duration_seconds": 0.0,
                            "energy_band_counts": {},
                            "duration_band_counts": {},
                            "position_band_counts": {},
                            "dominant_energy_band": None,
                            "opening_energy_band": None,
                            "closing_energy_band": None,
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.0,
                            "largest_abs_energy_delta": 0.0,
                            "transition_kind_counts": {},
                            "dominant_transition_kind": None,
                            "opening_transition_kind": None,
                            "closing_transition_kind": None,
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 0,
                            "sequence_occurrence_count": 0,
                            "sequence_signature_counts": {},
                            "sequence_signatures": [],
                            "dominant_sequence_signature": None,
                            "sequences": [],
                        },
                        "frame_count": 16000,
                        "spectral_extent_summary": {"low_hz": 90, "high_hz": 1200},
                        "channel_energy_summary": {"center_rms": 0.05},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_boundaries": [],
                    "section_candidates": [],
                    "section_transitions": [],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {"input_file_hash": "hash-review-same", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
            }

            left_changed_path.write_text(yaml.safe_dump(changed_left_document, sort_keys=False), encoding="utf-8")
            right_changed_path.write_text(yaml.safe_dump(changed_right_document, sort_keys=False), encoding="utf-8")
            serialized_same = yaml.safe_dump(unchanged_document, sort_keys=False)
            left_same_path.write_text(serialized_same, encoding="utf-8")
            right_same_path.write_text(serialized_same, encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "arwif-batch-review-analysis",
                "--left",
                str(left_changed_path),
                str(left_same_path),
                "--right",
                str(right_changed_path),
                str(right_same_path),
                "--output",
                str(review_report_path),
                "--json",
            )

            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 2)
            self.assertEqual(payload["changed_pairs"], 1)
            self.assertEqual(payload["unchanged_pairs"], 1)
            self.assertEqual(payload["invalid_pairs"], 0)
            self.assertEqual(payload["report_output"], str(review_report_path))
            self.assertEqual(payload["report_format"], "json")
            self.assertEqual(payload["diff_report"]["changed_pairs"], 1)
            self.assertEqual(payload["analysis"]["metadata_fields_changed_in_all_changed_pairs"], ["source_id"])
            self.assertIn("codec", payload["analysis"]["observed_audio_fields_changed_in_all_changed_pairs"])
            self.assertIn(
                "transition_motif_phrase_abstraction_ladder.recurring_counts.phrase",
                payload["analysis"]["basic_observation_fields_changed_in_all_changed_pairs"],
            )
            self.assertEqual(
                payload["analysis"]["analysis_change_summary"]["pairs_with_highest_stable_transition_motif_abstraction_layer_change"],
                1,
            )
            self.assertEqual(
                payload["analysis"]["analysis_change_summary"]["pairs_with_highest_stable_transition_motif_abstraction_layer_rise"],
                1,
            )
            self.assertEqual(
                payload["analysis"]["analysis_change_summary"]["total_highest_stable_transition_motif_abstraction_layer_step_delta"],
                9,
            )
            self.assertEqual(
                payload["diff_report"]["results"][0]["highest_stable_transition_motif_abstraction_layer_change"]["right"],
                {"layer": "gesture", "recurring_count": 1, "occurrence_count": 2},
            )
            self.assertEqual(payload["analysis"]["analysis_change_summary"]["pairs_with_section_transition_count_delta"], 1)
            self.assertEqual(payload["analysis"]["source_hypothesis_linked_transition_motif_signatures_added_in_all_changed_pairs"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_sequence_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_chain_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["analysis"]["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
                ["single_direction_sweep"],
            )
            self.assertEqual(payload["analysis"]["transition_motif_signatures_added_in_all_changed_pairs"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["analysis"]["transition_motif_sequence_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_chain_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_signatures_added_in_all_changed_pairs"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["analysis"]["transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
                ["single_direction_sweep"],
            )
            self.assertEqual(len(payload["diff_report"]["results"]), 2)

            persisted_review = json.loads(review_report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_review["pairs_compared"], 2)
            self.assertEqual(persisted_review["analysis"]["metadata_fields_changed_in_all_changed_pairs"], ["source_id"])

    def test_arwif_batch_review_analysis_reports_invalid_documents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_path = tmp_dir / "valid-analysis.yaml"
            missing_path = tmp_dir / "missing-analysis.yaml"

            valid_path.write_text(
                yaml.safe_dump(
                    {
                        "analysis_metadata": {
                            "analysis_profile": "basic-observation",
                            "analysis_version": "0.1-draft",
                            "analyzer_id": "rwif-builder",
                            "source_id": "demo.valid.review",
                        },
                        "observed_audio": {
                            "path_hint": ".local/audio/valid-review.wav",
                            "duration_seconds": 1.0,
                            "sample_rate_hz": 8000,
                            "channel_count": 1,
                            "codec": "wav",
                            "original_sample_rate_hz": 8000,
                            "original_channel_count": 1,
                            "analysis_window": {"start_seconds": 0.0, "duration_seconds": 1.0},
                        },
                        "observation_layers": {
                            "basic_observation_summary": {
                                "peak_amplitude": 0.1,
                                "rms_amplitude": 0.05,
                                "estimated_onset_count": 0,
                                "section_boundary_count": 0,
                                "section_candidate_count": 0,
                                "section_transition_count": 0,
                                "section_profile_summary": {
                                    "average_duration_seconds": 0.0,
                                    "longest_duration_seconds": 0.0,
                                    "energy_band_counts": {},
                                    "duration_band_counts": {},
                                    "position_band_counts": {},
                                    "dominant_energy_band": None,
                                    "opening_energy_band": None,
                                    "closing_energy_band": None,
                                },
                                "transition_profile_summary": {
                                    "average_abs_energy_delta": 0.0,
                                    "largest_abs_energy_delta": 0.0,
                                    "transition_kind_counts": {},
                                    "dominant_transition_kind": None,
                                    "opening_transition_kind": None,
                                    "closing_transition_kind": None,
                                },
                                "frame_count": 8000,
                                "spectral_extent_summary": {"low_hz": 90, "high_hz": 1000},
                                "channel_energy_summary": {"center_rms": 0.05},
                            },
                            "onset_map": [],
                            "transient_events": [],
                            "section_boundaries": [],
                            "section_candidates": [],
                            "section_transitions": [],
                        },
                        "source_hypotheses": [],
                        "component_layers": {},
                        "reconstruction": {"reconstructable_outputs": []},
                        "uncertainty_notes": {"warnings": []},
                        "provenance": {"input_file_hash": "hash-valid-review", "decode_backend": "wave", "preprocessing_steps": ["decode", "observe"]},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "arwif-batch-review-analysis",
                "--left",
                str(valid_path),
                str(valid_path),
                "--right",
                str(valid_path),
                str(missing_path),
                "--json",
                allow_failure=True,
            )

            self.assertFalse(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 2)
            self.assertEqual(payload["changed_pairs"], 0)
            self.assertEqual(payload["unchanged_pairs"], 2)
            self.assertEqual(payload["invalid_pairs"], 1)
            self.assertFalse(payload["diff_report"]["is_valid"])
            self.assertFalse(payload["analysis"]["is_valid"])
            invalid_result = next(result for result in payload["diff_report"]["results"] if result["right"] == str(missing_path))
            self.assertFalse(invalid_result["right_valid"])
            self.assertIn("does not exist", invalid_result["errors"][0])

    def test_arwif_diff_analysis_reports_summary_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-analysis.yaml"
            right_path = tmp_dir / "right-analysis.json"
            report_path = tmp_dir / "analysis-diff-report.yaml"

            left_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.left",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/left.wav",
                    "duration_seconds": 10.0,
                    "sample_rate_hz": 16000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 16000,
                    "original_channel_count": 1,
                    "analysis_window": {
                        "start_seconds": 0.0,
                        "duration_seconds": 10.0,
                    },
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.4,
                        "rms_amplitude": 0.1,
                        "estimated_onset_count": 8,
                        "section_boundary_count": 0,
                        "section_candidate_count": 1,
                        "section_profile_summary": {
                            "average_duration_seconds": 10.0,
                            "longest_duration_seconds": 10.0,
                            "energy_band_counts": {"medium": 1},
                            "duration_band_counts": {"long": 1},
                            "position_band_counts": {"middle": 1},
                            "dominant_energy_band": "medium",
                            "opening_energy_band": "medium",
                            "closing_energy_band": "medium",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.0,
                            "largest_abs_energy_delta": 0.0,
                            "transition_kind_counts": {},
                            "dominant_transition_kind": None,
                            "opening_transition_kind": None,
                            "closing_transition_kind": None,
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 0,
                            "motif_occurrence_count": 0,
                            "motif_signature_counts": {},
                            "motif_signatures": [],
                            "dominant_motif_signature": None,
                            "motifs": [],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 0,
                            "sequence_occurrence_count": 0,
                            "sequence_signature_counts": {},
                            "sequence_signatures": [],
                            "dominant_sequence_signature": None,
                            "sequences": [],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 0,
                            "chain_occurrence_count": 0,
                            "chain_signature_counts": {},
                            "chain_signatures": [],
                            "dominant_chain_signature": None,
                            "chains": [],
                        },
                        "frame_count": 160000,
                        "spectral_extent_summary": {"low_hz": 80, "high_hz": 4200},
                        "channel_energy_summary": {"center_rms": 0.1},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_candidates": [{"section_index": 0, "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "rms_amplitude": 0.1, "relative_energy": 1.0, "energy_band": "medium", "duration_band": "long", "position_band": "middle"}],
                    "section_transitions": [],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {
                    "input_file_hash": "hash-left",
                    "decode_backend": "wave",
                    "preprocessing_steps": ["decode", "observe"],
                },
            }
            right_document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.right",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/right.mp3",
                    "duration_seconds": 12.0,
                    "sample_rate_hz": 44100,
                    "channel_count": 2,
                    "codec": "mp3",
                    "original_sample_rate_hz": 44100,
                    "original_channel_count": 2,
                    "analysis_window": {
                        "start_seconds": 1.0,
                        "duration_seconds": 4.5,
                    },
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.8,
                        "rms_amplitude": 0.2,
                        "estimated_onset_count": 22,
                        "section_boundary_count": 1,
                        "section_candidate_count": 2,
                        "section_profile_summary": {
                            "average_duration_seconds": 2.25,
                            "longest_duration_seconds": 3.5,
                            "energy_band_counts": {"high": 1, "low": 1},
                            "duration_band_counts": {"medium": 1, "short": 1},
                            "position_band_counts": {"middle": 1, "opening": 1},
                            "dominant_energy_band": "high",
                            "opening_energy_band": "low",
                            "closing_energy_band": "high",
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.7,
                            "largest_abs_energy_delta": 0.7,
                            "transition_kind_counts": {"energy_increase": 1},
                            "dominant_transition_kind": "energy_increase",
                            "opening_transition_kind": "energy_increase",
                            "closing_transition_kind": "energy_increase",
                        },
                        "transition_motif_summary": {
                            "recurring_motif_count": 1,
                            "motif_occurrence_count": 2,
                            "motif_signature_counts": {"energy_increase|low|high|lengthen": 2},
                            "motif_signatures": ["energy_increase|low|high|lengthen"],
                            "dominant_motif_signature": "energy_increase|low|high|lengthen",
                            "motifs": [
                                {
                                    "motif_id": "transition_motif.01",
                                    "signature": "energy_increase|low|high|lengthen",
                                    "transition_kind": "energy_increase",
                                    "from_energy_band": "low",
                                    "to_energy_band": "high",
                                    "duration_trend": "lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_indexes": [0, 1],
                                    "boundary_offsets_seconds": [1.0, 3.0],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_sequence_summary": {
                            "recurring_sequence_count": 1,
                            "sequence_occurrence_count": 2,
                            "sequence_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_sequence_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "sequences": [
                                {
                                    "sequence_id": "transition_motif_sequence.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "left_signature": "energy_increase|low|high|lengthen",
                                    "right_signature": "energy_increase|low|high|lengthen",
                                    "occurrence_count": 2,
                                    "section_transition_index_pairs": [[0, 1], [1, 2]],
                                    "boundary_offset_pairs_seconds": [[1.0, 3.0], [3.0, 4.0]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_chain_summary": {
                            "chain_length": 3,
                            "recurring_chain_count": 1,
                            "chain_occurrence_count": 2,
                            "chain_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_chain_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "chains": [
                                {
                                    "chain_id": "transition_motif_chain.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "chain_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_chains": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_chains_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_phrase_count": 1,
                            "phrase_occurrence_count": 2,
                            "phrase_signature_counts": {"energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen": 2},
                            "phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                            "dominant_phrase_signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                            "phrases": [
                                {
                                    "phrase_id": "transition_motif_phrase.01",
                                    "signature": "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
                                    "motif_signatures": ["energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen", "energy_increase|low|high|lengthen"],
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_family_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_family_count": 1,
                            "family_occurrence_count": 2,
                            "family_signature_counts": {"energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen": 2},
                            "family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                            "dominant_family_signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                            "families": [
                                {
                                    "family_id": "transition_motif_phrase_family.01",
                                    "signature": "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
                                    "phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_archetype_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_archetype_count": 1,
                            "archetype_occurrence_count": 2,
                            "archetype_signature_counts": {"energy_increase|rise_band|lengthen": 2},
                            "archetype_signatures": ["energy_increase|rise_band|lengthen"],
                            "dominant_archetype_signature": "energy_increase|rise_band|lengthen",
                            "archetypes": [
                                {
                                    "archetype_id": "transition_motif_phrase_archetype.01",
                                    "signature": "energy_increase|rise_band|lengthen",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_contour_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_contour_count": 1,
                            "contour_occurrence_count": 2,
                            "contour_signature_counts": {"energy_increase|rise_band": 2},
                            "contour_signatures": ["energy_increase|rise_band"],
                            "dominant_contour_signature": "energy_increase|rise_band",
                            "contours": [
                                {
                                    "contour_id": "transition_motif_phrase_contour.01",
                                    "signature": "energy_increase|rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_sweep_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_sweep_count": 1,
                            "sweep_occurrence_count": 2,
                            "sweep_signature_counts": {"rise_band": 2},
                            "sweep_signatures": ["rise_band"],
                            "dominant_sweep_signature": "rise_band",
                            "sweeps": [
                                {
                                    "sweep_id": "transition_motif_phrase_sweep.01",
                                    "signature": "rise_band",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "transition_motif_phrase_gesture_summary": {
                            "min_phrase_length": 3,
                            "max_phrase_length": 5,
                            "recurring_gesture_count": 1,
                            "gesture_occurrence_count": 2,
                            "gesture_signature_counts": {"single_direction_sweep": 2},
                            "gesture_signatures": ["single_direction_sweep"],
                            "dominant_gesture_signature": "single_direction_sweep",
                            "gestures": [
                                {
                                    "gesture_id": "transition_motif_phrase_gesture.01",
                                    "signature": "single_direction_sweep",
                                    "min_phrase_length": 3,
                                    "max_phrase_length": 3,
                                    "occurrence_count": 2,
                                    "member_sweep_count": 1,
                                    "member_sweep_ids": ["transition_motif_phrase_sweep.01"],
                                    "member_sweep_signatures": ["rise_band"],
                                    "member_contour_count": 1,
                                    "member_contour_ids": ["transition_motif_phrase_contour.01"],
                                    "member_contour_signatures": ["energy_increase|rise_band"],
                                    "member_archetype_count": 1,
                                    "member_archetype_ids": ["transition_motif_phrase_archetype.01"],
                                    "member_archetype_signatures": ["energy_increase|rise_band|lengthen"],
                                    "member_family_count": 1,
                                    "member_family_ids": ["transition_motif_phrase_family.01"],
                                    "member_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
                                    "member_phrase_count": 1,
                                    "member_phrase_ids": ["transition_motif_phrase.01"],
                                    "member_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
                                    "section_transition_index_phrases": [[0, 1, 2], [1, 2, 3]],
                                    "boundary_offset_phrases_seconds": [[1.0, 3.0, 4.0], [3.0, 4.0, 4.25]],
                                    "time_bounds": {"start_seconds": 0.0, "end_seconds": 4.5, "duration_seconds": 4.5},
                                }
                            ],
                        },
                        "frame_count": 198450,
                        "spectral_extent_summary": {"low_hz": 60, "high_hz": 7200},
                        "channel_energy_summary": {"left_rms": 0.21, "right_rms": 0.19},
                    },
                    "onset_map": [{"offset_seconds": 0.5, "strength": 0.2}],
                    "transient_events": [],
                    "section_boundaries": [{"offset_seconds": 1.0, "confidence": 0.4, "energy_transition": "rise"}],
                    "section_candidates": [
                        {"section_index": 0, "start_seconds": 0.0, "end_seconds": 1.0, "duration_seconds": 1.0, "rms_amplitude": 0.1, "relative_energy": 0.5, "energy_band": "low", "duration_band": "short", "position_band": "opening"},
                        {"section_index": 1, "start_seconds": 1.0, "end_seconds": 4.5, "duration_seconds": 3.5, "rms_amplitude": 0.2, "relative_energy": 1.2, "energy_band": "high", "duration_band": "medium", "position_band": "middle"},
                    ],
                    "section_transitions": [
                        {"from_section_index": 0, "to_section_index": 1, "boundary_offset_seconds": 1.0, "from_energy_band": "low", "to_energy_band": "high", "energy_delta": 0.7, "duration_delta_seconds": 2.5, "transition_kind": "energy_increase"},
                    ],
                },
                "source_hypotheses": [{"source_id": "source.vocals.01", "source_class": "foreground_call_stream", "role": "foreground_stream", "linked_observations": {"transition_motif_signatures": ["energy_increase|low|high|lengthen"], "transition_motif_sequence_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_chain_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_signatures": ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"], "transition_motif_phrase_family_signatures": ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"], "transition_motif_phrase_archetype_signatures": ["energy_increase|rise_band|lengthen"], "transition_motif_phrase_contour_signatures": ["energy_increase|rise_band"], "transition_motif_phrase_sweep_signatures": ["rise_band"], "transition_motif_phrase_gesture_signatures": ["single_direction_sweep"]}}],
                "component_layers": {"harmonic_component_groups": [{"component_id": "component.01"}]},
                "reconstruction": {"reconstructable_outputs": ["vocals"]},
                "uncertainty_notes": {"warnings": ["lossy source"]},
                "attention_contract": {
                    "query_text": "Is there a foreground call to retain?",
                    "attention_targets": ["foreground call", "lead vocal motion"],
                    "retain_targets": ["foreground call"],
                    "suppress_targets": ["background bed"],
                    "answer_expectations": ["state whether a call-like foreground is present"],
                    "render_goal": "preserve the foreground call emphasis",
                },
                "interpretation_layers": {
                    "scene_hypotheses": [
                        {
                            "hypothesis_id": "scene.01",
                            "label": "foreground call over rising backing layer",
                            "confidence": 0.36,
                            "confidence_band": "low",
                            "hypothesis_origin": "task_conditioned_initialization",
                            "observed_source_classes": ["foreground_call_stream"],
                            "linked_source_ids": ["source.vocals.01"],
                            "attention_targets_matched_source_classes": ["foreground_call_stream"],
                            "attention_targets_unmatched": ["lead vocal motion"],
                        }
                    ],
                    "communicative_hypotheses": [
                        {
                            "hypothesis_id": "communicative.01",
                            "label": "foreground call likely carries the queried answer",
                            "confidence": 0.31,
                            "confidence_band": "low",
                            "hypothesis_origin": "task_conditioned_initialization",
                            "linked_source_classes": ["foreground_call_stream"],
                            "answer_expectations": ["state whether a call-like foreground is present"],
                        }
                    ],
                    "task_conditioning_notes": [
                        {
                            "note_id": "task-note.01",
                            "kind": "attention_bias",
                            "text": "Prioritize foreground-call evidence over accompaniment texture.",
                        }
                    ],
                },
                "transformation_intent": {
                    "operations": ["retain_foreground", "suppress_background"],
                    "primary_output": "foreground_call_stem",
                },
                "provenance": {
                    "input_file_hash": "hash-right",
                    "decode_backend": "ffmpeg",
                    "preprocessing_steps": ["decode", "observe", "window"],
                },
            }

            left_path.write_text(yaml.safe_dump(left_document, sort_keys=False), encoding="utf-8")
            right_path.write_text(json.dumps(right_document, indent=2), encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "arwif-diff-analysis",
                str(left_path),
                str(right_path),
                "--output",
                str(report_path),
                "--json",
            )

            self.assertTrue(payload["left_valid"])
            self.assertTrue(payload["right_valid"])
            self.assertTrue(payload["pair_changed"])
            self.assertEqual(payload["metadata_changes"]["source_id"]["left"], "demo.left")
            self.assertEqual(payload["metadata_changes"]["source_id"]["right"], "demo.right")
            self.assertEqual(payload["observed_audio_changes"]["codec"]["left"], "wav")
            self.assertEqual(payload["observed_audio_changes"]["codec"]["right"], "mp3")
            self.assertEqual(payload["observation_layer_changes"]["added"], ["section_boundaries"])
            self.assertEqual(payload["reconstructable_outputs_added"], ["vocals"])
            self.assertEqual(payload["source_hypothesis_class_changes"]["added"], ["foreground_call_stream"])
            self.assertEqual(payload["source_hypothesis_linked_transition_motif_signature_changes"]["added"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_sequence_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_chain_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_family_signature_changes"]["added"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_archetype_signature_changes"]["added"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_contour_signature_changes"]["added"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_sweep_signature_changes"]["added"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["source_hypothesis_linked_transition_motif_phrase_gesture_signature_changes"]["added"],
                ["single_direction_sweep"],
            )
            self.assertEqual(payload["transition_motif_signature_changes"]["added"], ["energy_increase|low|high|lengthen"])
            self.assertEqual(
                payload["transition_motif_sequence_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_chain_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_signature_changes"]["added"],
                ["energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_family_signature_changes"]["added"],
                ["energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_archetype_signature_changes"]["added"],
                ["energy_increase|rise_band|lengthen"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_contour_signature_changes"]["added"],
                ["energy_increase|rise_band"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_sweep_signature_changes"]["added"],
                ["rise_band"],
            )
            self.assertEqual(
                payload["transition_motif_phrase_gesture_signature_changes"]["added"],
                ["single_direction_sweep"],
            )
            self.assertEqual(payload["source_hypothesis_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_sequence_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_chain_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_family_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_archetype_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_contour_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_sweep_count_delta"], 1)
            self.assertEqual(payload["recurring_transition_motif_phrase_gesture_count_delta"], 1)
            self.assertEqual(payload["component_group_count_delta"], 1)
            self.assertEqual(payload["onset_map_count_delta"], 1)
            self.assertEqual(payload["section_boundary_count_delta"], 1)
            self.assertEqual(payload["section_candidate_count_delta"], 1)
            self.assertEqual(payload["section_transition_count_delta"], 1)
            self.assertEqual(payload["basic_observation_changes"]["section_profile_summary"]["dominant_energy_band"]["left"], "medium")
            self.assertEqual(payload["basic_observation_changes"]["section_profile_summary"]["dominant_energy_band"]["right"], "high")
            self.assertEqual(payload["basic_observation_changes"]["transition_profile_summary"]["dominant_transition_kind"]["right"], "energy_increase")
            self.assertEqual(payload["basic_observation_changes"]["transition_motif_summary"]["dominant_motif_signature"]["right"], "energy_increase|low|high|lengthen")
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_sequence_summary"]["dominant_sequence_signature"]["right"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_chain_summary"]["dominant_chain_signature"]["right"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_summary"]["dominant_phrase_signature"]["right"],
                "energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen=>energy_increase|low|high|lengthen",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_family_summary"]["dominant_family_signature"]["right"],
                "energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen=>energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_archetype_summary"]["dominant_archetype_signature"]["right"],
                "energy_increase|rise_band|lengthen",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_contour_summary"]["dominant_contour_signature"]["right"],
                "energy_increase|rise_band",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_sweep_summary"]["dominant_sweep_signature"]["right"],
                "rise_band",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_gesture_summary"]["dominant_gesture_signature"]["right"],
                "single_direction_sweep",
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_abstraction_ladder"]["recurring_counts"]["phrase"]["left"],
                0,
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_abstraction_ladder"]["recurring_counts"]["phrase"]["right"],
                1,
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_abstraction_ladder"]["recurring_counts"]["gesture"]["right"],
                1,
            )
            self.assertEqual(
                payload["basic_observation_changes"]["transition_motif_phrase_abstraction_ladder"]["occurrence_counts"]["phrase"]["right"],
                2,
            )
            self.assertEqual(
                payload["highest_stable_transition_motif_abstraction_layer_change"]["left"],
                {"layer": "none", "recurring_count": 0, "occurrence_count": 0},
            )
            self.assertEqual(
                payload["highest_stable_transition_motif_abstraction_layer_change"]["right"],
                {"layer": "gesture", "recurring_count": 1, "occurrence_count": 2},
            )
            self.assertTrue(payload["highest_stable_transition_motif_abstraction_layer_change"]["layer_changed"])
            self.assertEqual(payload["highest_stable_transition_motif_abstraction_layer_change"]["direction"], "rose")
            self.assertEqual(payload["highest_stable_transition_motif_abstraction_layer_change"]["layer_step_delta"], 9)
            self.assertEqual(
                payload["attention_contract_changes"]["query_text"]["right"],
                "Is there a foreground call to retain?",
            )
            self.assertEqual(
                payload["attention_contract_changes"]["render_goal"]["right"],
                "preserve the foreground call emphasis",
            )
            self.assertEqual(
                payload["interpretation_layer_changes"]["added"],
                ["communicative_hypotheses", "scene_hypotheses", "task_conditioning_notes"],
            )
            self.assertEqual(
                payload["first_scene_hypothesis_changes"]["label"]["right"],
                "foreground call over rising backing layer",
            )
            self.assertEqual(
                payload["first_communicative_hypothesis_changes"]["label"]["right"],
                "foreground call likely carries the queried answer",
            )
            self.assertEqual(
                payload["transformation_intent_changes"]["primary_output"]["right"],
                "foreground_call_stem",
            )
            self.assertEqual(payload["interpretation_hypothesis_count_delta"], 3)
            self.assertEqual(payload["uncertainty_warning_count_delta"], 1)
            self.assertEqual(payload["provenance_changes"]["decode_backend"]["left"], "wave")
            self.assertEqual(payload["provenance_changes"]["decode_backend"]["right"], "ffmpeg")
            self.assertEqual(payload["report_format"], "yaml")
            self.assertTrue(report_path.exists())

    def test_arwif_diff_analysis_reports_no_change_for_identical_documents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-analysis.yaml"
            right_path = tmp_dir / "right-analysis.yaml"

            document = {
                "analysis_metadata": {
                    "analysis_profile": "basic-observation",
                    "analysis_version": "0.1-draft",
                    "analyzer_id": "rwif-builder",
                    "source_id": "demo.same",
                },
                "observed_audio": {
                    "path_hint": ".local/audio/same.wav",
                    "duration_seconds": 3.0,
                    "sample_rate_hz": 8000,
                    "channel_count": 1,
                    "codec": "wav",
                    "original_sample_rate_hz": 8000,
                    "original_channel_count": 1,
                    "analysis_window": {
                        "start_seconds": 0.0,
                        "duration_seconds": 3.0,
                    },
                },
                "observation_layers": {
                    "basic_observation_summary": {
                        "peak_amplitude": 0.2,
                        "rms_amplitude": 0.05,
                        "estimated_onset_count": 2,
                        "section_boundary_count": 0,
                        "section_candidate_count": 0,
                        "section_profile_summary": {
                            "average_duration_seconds": 0.0,
                            "longest_duration_seconds": 0.0,
                            "energy_band_counts": {},
                            "duration_band_counts": {},
                            "position_band_counts": {},
                            "dominant_energy_band": None,
                            "opening_energy_band": None,
                            "closing_energy_band": None,
                        },
                        "transition_profile_summary": {
                            "average_abs_energy_delta": 0.0,
                            "largest_abs_energy_delta": 0.0,
                            "transition_kind_counts": {},
                            "dominant_transition_kind": None,
                            "opening_transition_kind": None,
                            "closing_transition_kind": None,
                        },
                        "frame_count": 24000,
                        "spectral_extent_summary": {"low_hz": 90, "high_hz": 1000},
                        "channel_energy_summary": {"center_rms": 0.05},
                    },
                    "onset_map": [],
                    "transient_events": [],
                    "section_candidates": [],
                    "section_transitions": [],
                },
                "source_hypotheses": [],
                "component_layers": {},
                "reconstruction": {"reconstructable_outputs": []},
                "uncertainty_notes": {"warnings": []},
                "provenance": {
                    "input_file_hash": "hash-same",
                    "decode_backend": "wave",
                    "preprocessing_steps": ["decode", "observe"],
                },
            }

            serialized = yaml.safe_dump(document, sort_keys=False)
            left_path.write_text(serialized, encoding="utf-8")
            right_path.write_text(serialized, encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "arwif-diff-analysis",
                str(left_path),
                str(right_path),
                "--json",
            )

            self.assertTrue(payload["left_valid"])
            self.assertTrue(payload["right_valid"])
            self.assertFalse(payload["pair_changed"])
            self.assertEqual(payload["metadata_changes"], {})
            self.assertEqual(payload["observed_audio_changes"], {})
            self.assertEqual(payload["analysis_window_changes"], {})
            self.assertEqual(payload["basic_observation_changes"], {})
            self.assertEqual(payload["source_hypothesis_count_delta"], 0)
            self.assertEqual(payload["component_group_count_delta"], 0)
            self.assertEqual(payload["onset_map_count_delta"], 0)
            self.assertEqual(payload["section_boundary_count_delta"], 0)
            self.assertEqual(payload["section_candidate_count_delta"], 0)
            self.assertEqual(payload["section_transition_count_delta"], 0)

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
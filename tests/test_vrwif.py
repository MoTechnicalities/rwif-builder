from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class VRWIFValidationTest(unittest.TestCase):
    def test_vrwif_validate_spec_accepts_scene_identity_bridge_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "vrwif_version: 1",
                        "scene_id: atrium.scene-01",
                        "reference_frame: scene",
                        "title: Atrium scene",
                        "objects:",
                        "  - object_id: bell.source",
                        "    object_groups:",
                        "      - foreground",
                        "      - percussion",
                        "    appearance_class: bell",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.2",
                        "      z: 2.0",
                        "    orientation:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.2",
                        "          z: 2.0",
                        "      - offset_seconds: 0.5",
                        "        position:",
                        "          x: 0.4",
                        "          y: 1.2",
                        "          z: 2.2",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -3.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: key.01",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 2.5",
                        "    color: warm",
                        "    temperature_kelvin: 3200",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-validate-spec", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["stats"]["scene_id"], "atrium.scene-01")
            self.assertEqual(payload["stats"]["reference_frame"], "scene")
            self.assertEqual(payload["stats"]["object_count"], 1)
            self.assertEqual(payload["stats"]["objects_with_trajectory"], 1)
            self.assertEqual(payload["stats"]["object_trajectory_point_count"], 2)
            self.assertTrue(payload["stats"]["camera_present"])
            self.assertEqual(payload["stats"]["light_count"], 1)
            self.assertEqual(payload["stats"]["object_groups"], ["foreground", "percussion"])
            self.assertEqual(payload["stats"]["appearance_classes"], ["bell"])

    def test_vrwif_inspect_reports_scene_summary(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "inspect-scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "scene_id: hall.scene-02",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.left",
                        "    object_groups:",
                        "      - foreground",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: -1.0",
                        "      y: 0.0",
                        "      z: 2.0",
                        "    orientation:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "  - object_id: object.right",
                        "    object_groups:",
                        "      - background",
                        "    appearance_class: pillar",
                        "    position:",
                        "      x: 1.5",
                        "      y: 0.0",
                        "      z: 3.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 1.5",
                        "          y: 0.0",
                        "          z: 3.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.8",
                        "          y: 0.0",
                        "          z: 3.2",
                        "camera:",
                        "  camera_id: cam.inspect",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: fill.01",
                        "    direction:",
                        "      x: 0.2",
                        "      y: -0.8",
                        "      z: 0.5",
                        "    intensity: 1.25",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-inspect", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["scene_id"], "hall.scene-02")
            self.assertEqual(payload["reference_frame"], "world")
            self.assertEqual(payload["object_count"], 2)
            self.assertEqual(payload["objects"][0]["object_id"], "object.left")
            self.assertEqual(payload["objects"][1]["trajectory"][1]["position"]["x"], 1.8)
            self.assertEqual(payload["camera"]["camera_id"], "cam.inspect")
            self.assertEqual(payload["lighting"][0]["light_id"], "fill.01")
            self.assertEqual(payload["scene_summary"]["positioned_objects"], 2)
            self.assertEqual(payload["scene_summary"]["objects_with_orientation"], 1)
            self.assertEqual(payload["scene_summary"]["objects_with_trajectory"], 1)
            self.assertEqual(payload["scene_summary"]["object_trajectory_point_count"], 2)
            self.assertEqual(payload["scene_summary"]["light_count"], 1)
            self.assertEqual(payload["scene_summary"]["object_groups"], ["background", "foreground"])

    def test_vrwif_diff_reports_scene_and_object_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-scene.yaml"
            right_path = tmp_dir / "right-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: courtyard.scene",
                        "reference_frame: scene",
                        "title: Courtyard left",
                        "objects:",
                        "  - object_id: object.tree",
                        "    object_groups:",
                        "      - nature",
                        "    appearance_class: tree",
                        "    position:",
                        "      x: -1.0",
                        "      y: 0.0",
                        "      z: 4.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -5.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: key.left",
                        "    position:",
                        "      x: -2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    intensity: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: courtyard.scene",
                        "reference_frame: world",
                        "title: Courtyard right",
                        "objects:",
                        "  - object_id: object.tree",
                        "    object_groups:",
                        "      - nature",
                        "      - focal",
                        "    appearance_class: tree",
                        "    position:",
                        "      x: -0.5",
                        "      y: 0.0",
                        "      z: 3.5",
                        "  - object_id: object.bench",
                        "    object_groups:",
                        "      - prop",
                        "    appearance_class: bench",
                        "    position:",
                        "      x: 0.8",
                        "      y: 0.0",
                        "      z: 2.2",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.8",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: key.right",
                        "    position:",
                        "      x: 2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    intensity: 2.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["left_valid"], payload)
            self.assertTrue(payload["right_valid"], payload)
            self.assertIn("reference_frame", payload["metadata_changes"])
            self.assertIn("title", payload["metadata_changes"])
            self.assertEqual(payload["change_summary"]["added_objects"], 1)
            self.assertEqual(payload["change_summary"]["changed_objects"], 1)
            self.assertIn("object.bench", payload["added_objects"])
            self.assertIn("object.tree", payload["changed_objects"])
            self.assertTrue(payload["scene_changes"]["reference_frame_changed"])
            self.assertTrue(payload["scene_changes"]["object_groups_changed"])
            self.assertTrue(payload["scene_changes"]["camera_changed"])
            self.assertEqual(payload["scene_changes"]["light_count_delta"], 0)
            self.assertTrue(payload["scene_changes"]["light_ids_changed"])
            self.assertIn("position", payload["object_changes"]["object.tree"]["field_changes"])

    def test_vrwif_batch_inspect_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first-scene.yaml"
            second_path = tmp_dir / "second-scene.yaml"
            report_path = tmp_dir / "vrwif-batch-inspect-report.json"

            first_path.write_text(
                "\n".join(
                    [
                        "scene_id: scene.one",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - alpha",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            second_path.write_text(
                "\n".join(
                    [
                        "scene_id: scene.two",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - beta",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 2.0",
                        "camera:",
                        "  camera_id: cam.two",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -3.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "vrwif-batch-inspect",
                str(first_path),
                str(second_path),
                "--output",
                str(report_path),
                "--json",
            )
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["specs_processed"], 2)
            self.assertEqual(payload["valid_count"], 2)
            self.assertEqual(payload["total_object_count"], 2)
            self.assertEqual(payload["scenes_with_camera"], 1)
            self.assertTrue(report_path.exists())

    def test_vrwif_batch_diff_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_a = tmp_dir / "left-a.yaml"
            right_a = tmp_dir / "right-a.yaml"
            left_b = tmp_dir / "left-b.yaml"
            right_b = tmp_dir / "right-b.yaml"
            report_path = tmp_dir / "vrwif-batch-diff-report.json"

            left_a.write_text(
                "\n".join(
                    [
                        "scene_id: batch.a",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.a",
                        "    object_groups:",
                        "      - alpha",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_a.write_text(
                "\n".join(
                    [
                        "scene_id: batch.a",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.a",
                        "    object_groups:",
                        "      - alpha",
                        "      - moved",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            left_b.write_text(
                "\n".join(
                    [
                        "scene_id: batch.b",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.b",
                        "    object_groups:",
                        "      - beta",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 2.0",
                        "      y: 0.0",
                        "      z: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_b.write_text(left_b.read_text(encoding="utf-8"), encoding="utf-8")

            payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_a),
                str(left_b),
                "--right",
                str(right_a),
                str(right_b),
                "--output",
                str(report_path),
                "--json",
            )
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 2)
            self.assertEqual(payload["changed_pairs"], 1)
            self.assertEqual(payload["unchanged_pairs"], 1)
            self.assertEqual(payload["total_metadata_fields_changed"], 1)
            self.assertEqual(payload["total_changed_objects"], 1)
            self.assertTrue(report_path.exists())

    def test_vrwif_normalize_spec_canonicalizes_aliases_order_and_trajectories(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            source_path = tmp_dir / "loose-scene.yaml"
            normalized_path = tmp_dir / "normalized-scene.yaml"
            report_path = tmp_dir / "normalized-scene.report.json"

            source_path.write_text(
                "\n".join(
                    [
                        "scene_id: '  courtyard.scene  '",
                        "reference_frame: WORLD",
                        "objects:",
                        "  - object_id: object.b",
                        "    object_groups:",
                        "      - beta",
                        "      - alpha",
                        "      - beta",
                        "    class: statue",
                        "    position:",
                        "      z: 1",
                        "      y: 0",
                        "      x: 2",
                        "    trajectory:",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 2.5",
                        "          y: 0.0",
                        "          z: 1.0",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 1.0",
                        "  - object_id: object.a",
                        "    object_groups:",
                        "      - alpha",
                        "    appearance_class: bell",
                        "    position:",
                        "      x: 0",
                        "      y: 1",
                        "      z: 2",
                        "camera:",
                        "  camera_id: ' cam.main '",
                        "  position:",
                        "    x: 0",
                        "    y: 1.6",
                        "    z: -3",
                        "  orientation:",
                        "    x: 0",
                        "    y: 0",
                        "    z: 1",
                        "  trajectory:",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.6",
                        "        z: -2.0",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.6",
                        "        z: -3.0",
                        "lighting:",
                        "  - light_id: light.b",
                        "    intensity: 1",
                        "    direction:",
                        "      x: 0",
                        "      y: -1",
                        "      z: 0.5",
                        "  - light_id: light.a",
                        "    intensity: 2",
                        "    position:",
                        "      x: 1",
                        "      y: 2",
                        "      z: -1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "vrwif-normalize",
                str(source_path),
                "--output",
                str(normalized_path),
                "--report",
                str(report_path),
                "--json",
            )
            self.assertTrue(payload["normalized"], payload)
            self.assertFalse(payload["source_is_valid"])
            self.assertTrue(payload["normalized_spec_is_valid"])
            self.assertEqual(payload["normalization_summary"]["resolved_class_aliases"], 1)
            self.assertEqual(payload["normalization_summary"]["deduplicated_object_groups"], 1)
            self.assertEqual(payload["normalization_summary"]["sorted_object_trajectories"], 1)
            self.assertEqual(payload["normalization_summary"]["sorted_camera_trajectory"], 1)
            self.assertEqual(payload["normalization_summary"]["reordered_objects"], 1)
            self.assertEqual(payload["normalization_summary"]["reordered_lights"], 1)
            self.assertTrue(normalized_path.exists())
            self.assertEqual(payload["report_output"], str(report_path))
            self.assertEqual(payload["report_format"], "json")
            self.assertTrue(report_path.exists())

            report_document = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["report_version"], 1)
            self.assertEqual(report_document["spec"], str(source_path))
            self.assertEqual(report_document["spec_output"], str(normalized_path))
            self.assertFalse(report_document["source_validation"]["is_valid"])
            self.assertTrue(report_document["normalized_validation"]["is_valid"])
            self.assertEqual(report_document["normalized_document"]["reference_frame"], "world")

            inspect_payload = self._run_json(repo_root, "vrwif-inspect", str(normalized_path), "--json")
            self.assertEqual(inspect_payload["reference_frame"], "world")
            self.assertEqual(inspect_payload["objects"][0]["object_id"], "object.a")
            self.assertEqual(inspect_payload["objects"][1]["appearance_class"], "statue")
            self.assertEqual(inspect_payload["objects"][1]["object_groups"], ["alpha", "beta"])
            self.assertEqual(inspect_payload["objects"][1]["trajectory"][0]["offset_seconds"], 0.0)
            self.assertEqual(inspect_payload["camera"]["camera_id"], "cam.main")
            self.assertEqual(inspect_payload["lighting"][0]["light_id"], "light.a")

    def test_vrwif_batch_normalize_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first.yaml"
            second_path = tmp_dir / "second.yaml"
            output_dir = tmp_dir / "normalized"
            report_dir = tmp_dir / "reports"
            report_path = tmp_dir / "vrwif-batch-normalize-report.json"

            first_path.write_text(
                "\n".join(
                    [
                        "scene_id: first.scene",
                        "reference_frame: SCENE",
                        "objects:",
                        "  - object_id: object.first",
                        "    object_groups:",
                        "      - zeta",
                        "      - alpha",
                        "    class: prop",
                        "    position:",
                        "      x: 0",
                        "      y: 0",
                        "      z: 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            second_path.write_text(
                "\n".join(
                    [
                        "scene_id: second.scene",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.second",
                        "    object_groups:",
                        "      - beta",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 1",
                        "      y: 0",
                        "      z: 2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "vrwif-batch-normalize",
                str(first_path),
                str(second_path),
                "--output-dir",
                str(output_dir),
                "--report-dir",
                str(report_dir),
                "--output",
                str(report_path),
                "--json",
            )
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["specs_processed"], 2)
            self.assertEqual(payload["normalized_count"], 2)
            self.assertEqual(payload["failed_count"], 0)
            self.assertEqual(payload["total_object_count"], 2)
            self.assertEqual(payload["report_dir"], str(report_dir))
            self.assertTrue((output_dir / "first.normalized.yaml").exists())
            self.assertTrue((output_dir / "second.normalized.yaml").exists())
            self.assertTrue((report_dir / "first.normalized.report.json").exists())
            self.assertTrue((report_dir / "second.normalized.report.json").exists())
            self.assertTrue(report_path.exists())

    def test_vrwif_batch_diff_analyze_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_a = tmp_dir / "left-a.yaml"
            right_a = tmp_dir / "right-a.yaml"
            left_b = tmp_dir / "left-b.yaml"
            right_b = tmp_dir / "right-b.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-diff-report.json"
            analysis_report_path = tmp_dir / "vrwif-batch-diff-analysis.json"

            left_a.write_text(
                "\n".join(
                    [
                        "scene_id: analyze.a",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - base",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.a",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -3.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: light.a",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_a.write_text(
                "\n".join(
                    [
                        "scene_id: analyze.a",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - base",
                        "      - focus",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.a",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -3.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "lighting:",
                        "  - light_id: light.a",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            left_b.write_text(
                "\n".join(
                    [
                        "scene_id: analyze.b",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.beta",
                        "    object_groups:",
                        "      - support",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 2.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "camera:",
                        "  camera_id: cam.b",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.6",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_b.write_text(
                "\n".join(
                    [
                        "scene_id: analyze.b",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.beta",
                        "    object_groups:",
                        "      - support",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 2.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "camera:",
                        "  camera_id: cam.b",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.9",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_a),
                str(left_b),
                "--right",
                str(right_a),
                str(right_b),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)
            self.assertEqual(diff_payload["changed_pairs"], 2)
            self.assertEqual(diff_payload["unchanged_pairs"], 0)
            self.assertTrue(diff_payload["results"][1]["pair_changed"])

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["pairs_compared"], 2)
            self.assertEqual(analysis_payload["changed_pairs"], 2)
            self.assertEqual(analysis_payload["metadata_field_frequencies"][0]["field"], "reference_frame")
            self.assertEqual(analysis_payload["changed_object_frequencies"][0]["object"], "object.alpha")
            self.assertEqual(analysis_payload["scene_change_summary"]["reference_frame_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_changed_pairs"], 1)
            self.assertEqual(analysis_payload["objects_changed_in_all_changed_pairs"], [])
            self.assertEqual(analysis_payload["analysis_input"], str(diff_report_path))
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_review_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-scene.yaml"
            right_path = tmp_dir / "right-scene.yaml"
            review_report_path = tmp_dir / "vrwif-batch-review-report.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: review.scene",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - alpha",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "lighting:",
                        "  - light_id: light.left",
                        "    position:",
                        "      x: -1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: review.scene",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - alpha",
                        "    appearance_class: statue",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 1.0",
                        "lighting:",
                        "  - light_id: light.right",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "vrwif-batch-review",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(review_report_path),
                "--json",
            )
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["pairs_compared"], 1)
            self.assertEqual(payload["changed_pairs"], 1)
            self.assertEqual(payload["diff_report"]["changed_pairs"], 1)
            self.assertEqual(payload["analysis"]["scene_change_summary"]["light_ids_changed_pairs"], 1)
            self.assertTrue(review_report_path.exists())

    def test_vrwif_validate_spec_rejects_invalid_scene_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid-scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "vrwif_version: 2",
                        "scene_id: ''",
                        "reference_frame: listener",
                        "objects:",
                        "  - object_id: ''",
                        "    object_groups:",
                        "      - ok",
                        "      - ''",
                        "    class: ''",
                        "    position:",
                        "      x: left",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: ''",
                        "  position:",
                        "    x: 0.0",
                        "    y: nope",
                        "    z: -1.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "lighting:",
                        "  - light_id: ''",
                        "    intensity: -1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-validate-spec", str(spec_path), "--json", allow_failure=True)
            self.assertFalse(payload["is_valid"])
            self.assertIn("vrwif_version must be 1", payload["errors"])
            self.assertIn("scene_id must be a non-empty string", payload["errors"])
            self.assertIn("reference_frame must be one of: scene, world", payload["errors"])
            self.assertIn("objects[0].object_id must be a non-empty string", payload["errors"])
            self.assertIn("objects[0].object_groups[1] must be a non-empty string", payload["errors"])
            self.assertIn("objects[0].appearance_class must be a non-empty string", payload["errors"])
            self.assertIn("objects[0].position.x must be a finite number", payload["errors"])
            self.assertIn("camera.camera_id must be a non-empty string", payload["errors"])
            self.assertIn("camera.position.y must be a finite number", payload["errors"])
            self.assertIn("camera.orientation.z must be a finite number", payload["errors"])
            self.assertIn("lighting[0].light_id must be a non-empty string", payload["errors"])
            self.assertIn("lighting[0] must define position or direction", payload["errors"])
            self.assertIn("lighting[0].intensity must be a non-negative finite number", payload["errors"])

    def test_vrwif_batch_validate_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            valid_path = tmp_dir / "valid-scene.yaml"
            invalid_path = tmp_dir / "invalid-scene.yaml"
            report_path = tmp_dir / "vrwif-batch-report.json"

            valid_path.write_text(
                "\n".join(
                    [
                        "scene_id: scene.valid",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.a",
                        "    object_groups:",
                        "      - set-a",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            invalid_path.write_text(
                "\n".join(
                    [
                        "scene_id: scene.invalid",
                        "reference_frame: nowhere",
                        "objects: []",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(
                repo_root,
                "vrwif-batch-validate-spec",
                str(valid_path),
                str(invalid_path),
                "--output",
                str(report_path),
                "--json",
                allow_failure=True,
            )
            self.assertFalse(payload["is_valid"])
            self.assertEqual(payload["specs_processed"], 2)
            self.assertEqual(payload["valid_count"], 1)
            self.assertEqual(payload["invalid_count"], 1)
            self.assertEqual(payload["total_object_count"], 1)
            self.assertEqual(payload["total_light_count"], 0)
            self.assertTrue(report_path.exists())

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
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
                        "    state: active",
                        "    visibility: visible",
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
                        "  framing_intent: centered-medium",
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
            self.assertEqual(payload["stats"]["camera_framing_intent"], "centered-medium")
            self.assertEqual(payload["stats"]["light_count"], 1)
            self.assertEqual(payload["stats"]["light_colors"], ["warm"])
            self.assertEqual(payload["normalized_document"]["lighting"][0]["position"]["x"], 1.0)
            self.assertEqual(payload["stats"]["object_groups"], ["foreground", "percussion"])
            self.assertEqual(payload["stats"]["appearance_classes"], ["bell"])
            self.assertEqual(payload["stats"]["object_states"], ["active"])
            self.assertEqual(payload["stats"]["object_visibilities"], ["visible"])

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
                        "    state: idle",
                        "    visibility: visible",
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
                        "    state: transitioning",
                        "    visibility: occluded",
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
                        "  framing_intent: subject-focused",
                        "lighting:",
                        "  - light_id: fill.01",
                        "    direction:",
                        "      x: 0.2",
                        "      y: -0.8",
                        "      z: 0.5",
                        "    intensity: 1.25",
                        "    color: cool",
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
            self.assertEqual(payload["objects"][0]["state"], "idle")
            self.assertEqual(payload["objects"][0]["visibility"], "visible")
            self.assertEqual(payload["objects"][1]["trajectory"][1]["position"]["x"], 1.8)
            self.assertEqual(payload["camera"]["camera_id"], "cam.inspect")
            self.assertEqual(payload["camera"]["framing_intent"], "subject-focused")
            self.assertEqual(payload["lighting"][0]["light_id"], "fill.01")
            self.assertEqual(payload["lighting"][0]["color"], "cool")
            self.assertEqual(payload["scene_summary"]["positioned_objects"], 2)
            self.assertAlmostEqual(payload["scene_summary"]["object_distance_from_origin_total"], 5.5901699437494745)
            self.assertAlmostEqual(payload["scene_summary"]["object_distance_from_origin_range"]["min"], 2.23606797749979)
            self.assertAlmostEqual(payload["scene_summary"]["object_distance_from_origin_range"]["max"], 3.3541019662496847)
            self.assertEqual(payload["scene_summary"]["objects_with_orientation"], 1)
            self.assertEqual(payload["scene_summary"]["objects_with_trajectory"], 1)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_duration_total"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_duration_range"]["min"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_duration_range"]["max"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_path_length_total"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_path_length_range"]["min"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_path_length_range"]["max"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_displacement_total"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_displacement_range"]["min"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_displacement_range"]["max"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_speed_total"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_speed_range"]["min"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_speed_range"]["max"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_speed_total"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_speed_range"]["min"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_speed_range"]["max"], 0.36055512754639907)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_speed_standard_deviation_total"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_speed_standard_deviation_range"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_speed_standard_deviation_range"]["max"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_acceleration_total"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_acceleration_range"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_acceleration_range"]["max"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_acceleration_total"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_acceleration_range"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_acceleration_range"]["max"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_straightness_total"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_straightness_range"]["min"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_straightness_range"]["max"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_total_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_range_degrees"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_range_degrees"]["max"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_turn_angle_total_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_turn_angle_range_degrees"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_peak_turn_angle_range_degrees"]["max"], 0.0)
            self.assertEqual(payload["scene_summary"]["object_trajectory_turn_count_total"], 0)
            self.assertEqual(payload["scene_summary"]["object_trajectory_turn_count_range"]["min"], 0)
            self.assertEqual(payload["scene_summary"]["object_trajectory_turn_count_range"]["max"], 0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_turn_angle_total_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_turn_angle_range_degrees"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_average_turn_angle_range_degrees"]["max"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_standard_deviation_total_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_standard_deviation_range_degrees"]["min"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["object_trajectory_turn_angle_standard_deviation_range_degrees"]["max"], 0.0)
            self.assertEqual(payload["scene_summary"]["object_trajectory_point_count"], 2)
            self.assertAlmostEqual(payload["scene_summary"]["camera_distance_from_origin"], 4.308131845707604)
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_duration"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_path_length"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_displacement"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_average_speed"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_peak_speed"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_speed_standard_deviation"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_average_acceleration"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_straightness"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_turn_angle_degrees"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_peak_turn_angle_degrees"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_turn_count"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_average_turn_angle_degrees"])
            self.assertIsNone(payload["scene_summary"]["camera_trajectory_turn_angle_standard_deviation_degrees"])
            self.assertEqual(payload["scene_summary"]["camera_framing_intent"], "subject-focused")
            self.assertTrue(payload["scene_summary"]["lighting_present"])
            self.assertEqual(payload["scene_summary"]["light_count"], 1)
            self.assertEqual(payload["scene_summary"]["light_intensity_total"], 1.25)
            self.assertEqual(payload["scene_summary"]["light_intensity_range"], {"min": 1.25, "max": 1.25})
            self.assertEqual(payload["scene_summary"]["light_colors"], ["cool"])
            self.assertEqual(payload["scene_summary"]["positioned_lights"], 0)
            self.assertEqual(payload["scene_summary"]["directional_lights"], 1)
            self.assertEqual(payload["scene_summary"]["lights_with_temperature"], 0)
            self.assertIsNone(payload["scene_summary"]["light_temperature_range_kelvin"])
            self.assertEqual(payload["scene_summary"]["object_groups"], ["background", "foreground"])
            self.assertEqual(payload["scene_summary"]["object_states"], ["idle", "transitioning"])
            self.assertEqual(payload["scene_summary"]["object_visibilities"], ["occluded", "visible"])

    def test_vrwif_inspect_reports_light_temperature_summary(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "inspect-temperature-scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "scene_id: temperature.scene",
                        "reference_frame: world",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.warm",
                        "    position:",
                        "      x: -1.0",
                        "      y: 2.0",
                        "      z: 0.5",
                        "    intensity: 1.0",
                        "    temperature_kelvin: 3200",
                        "  - light_id: light.cool",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.0",
                        "    intensity: 0.8",
                        "    temperature_kelvin: 5600",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-inspect", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["scene_summary"]["light_intensity_total"], 1.8)
            self.assertEqual(payload["scene_summary"]["light_intensity_range"], {"min": 0.8, "max": 1.0})
            self.assertEqual(payload["scene_summary"]["lights_with_temperature"], 2)
            self.assertEqual(payload["scene_summary"]["light_temperature_range_kelvin"], {"min": 3200.0, "max": 5600.0})

    def test_vrwif_inspect_exposes_metadata_and_realm_references(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "inspect-bridge-scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "scene_id: bridge.scene",
                        "reference_frame: scene",
                        "metadata:",
                        "  sequence_family: atrium-demo",
                        "  related_realms:",
                        "    - realm: rwif",
                        "      role: semantic_memory",
                        "      artifact: memory/bridge.rwif",
                        "    - realm: arwif",
                        "      role: soundscape",
                        "      artifact: audio/bridge.arwif",
                        "objects:",
                        "  - object_id: bell.source",
                        "    object_groups:",
                        "      - foreground",
                        "    appearance_class: bell",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.2",
                        "      z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-inspect", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["metadata"]["sequence_family"], "atrium-demo")
            self.assertEqual(len(payload["realm_references"]), 2)
            self.assertEqual(payload["realm_references"][0]["realm"], "rwif")
            self.assertEqual(payload["realm_references"][1]["realm"], "arwif")
            self.assertEqual(payload["realm_references"][0]["artifact"], "memory/bridge.rwif")

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
                        "    state: idle",
                        "    visibility: visible",
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
                        "  framing_intent: centered-medium",
                        "lighting:",
                        "  - light_id: key.left",
                        "    position:",
                        "      x: -2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    intensity: 2.0",
                        "    color: warm",
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
                        "    state: active",
                        "    visibility: occluded",
                        "  - object_id: object.bench",
                        "    object_groups:",
                        "      - prop",
                        "    appearance_class: bench",
                        "    position:",
                        "      x: 0.8",
                        "      y: 0.0",
                        "      z: 2.2",
                        "    state: idle",
                        "    visibility: visible",
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
                        "  framing_intent: detail-close",
                        "lighting:",
                        "  - light_id: key.right",
                        "    position:",
                        "      x: 2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    intensity: 2.5",
                        "    color: cool",
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
            self.assertEqual(payload["scene_changes"]["object_count_delta"], 1)
            self.assertTrue(payload["scene_changes"]["object_ids_changed"])
            self.assertTrue(payload["scene_changes"]["object_groups_changed"])
            self.assertEqual(payload["scene_changes"]["object_groups_count_delta"], 2)
            self.assertTrue(payload["scene_changes"]["appearance_classes_changed"])
            self.assertEqual(payload["scene_changes"]["appearance_classes_count_delta"], 1)
            self.assertTrue(payload["scene_changes"]["camera_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_distance_from_origin_total_delta"], 1.753368262458999)
            self.assertTrue(payload["scene_changes"]["object_distance_from_origin_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_duration_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_duration_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_path_length_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_path_length_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_displacement_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_displacement_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_average_speed_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_average_speed_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_peak_speed_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_peak_speed_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_speed_standard_deviation_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_speed_standard_deviation_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_straightness_total_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_straightness_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_turn_angle_total_degrees_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_turn_angle_range_degrees_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_peak_turn_angle_total_degrees_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_peak_turn_angle_range_degrees_changed"])
            self.assertEqual(payload["scene_changes"]["object_trajectory_turn_count_total_delta"], 0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_turn_count_range_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_average_turn_angle_total_degrees_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_average_turn_angle_range_degrees_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_turn_angle_standard_deviation_total_degrees_delta"], 0.0)
            self.assertFalse(payload["scene_changes"]["object_trajectory_turn_angle_standard_deviation_range_degrees_changed"])
            self.assertAlmostEqual(payload["scene_changes"]["camera_distance_from_origin_delta"], -0.8634194594704132)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_duration_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_path_length_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_displacement_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_speed_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_peak_speed_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_speed_standard_deviation_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_acceleration_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_straightness_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_turn_angle_degrees_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_peak_turn_angle_degrees_delta"], 0.0)
            self.assertEqual(payload["scene_changes"]["camera_trajectory_turn_count_delta"], 0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_turn_angle_degrees_delta"], 0.0)
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_turn_angle_standard_deviation_degrees_delta"], 0.0)
            self.assertEqual(payload["scene_changes"]["camera_trajectory_point_count_delta"], 0)
            self.assertFalse(payload["scene_changes"]["camera_present_changed"])
            self.assertTrue(payload["scene_changes"]["framing_intent_changed"])
            self.assertFalse(payload["scene_changes"]["camera_id_changed"])
            self.assertFalse(payload["scene_changes"]["camera_has_trajectory_changed"])
            self.assertTrue(payload["scene_changes"]["object_states_changed"])
            self.assertTrue(payload["scene_changes"]["object_visibilities_changed"])
            self.assertFalse(payload["scene_changes"]["lighting_present_changed"])
            self.assertEqual(payload["scene_changes"]["light_count_delta"], 0)
            self.assertEqual(payload["scene_changes"]["light_intensity_total_delta"], 0.5)
            self.assertTrue(payload["scene_changes"]["light_intensity_range_changed"])
            self.assertEqual(payload["scene_changes"]["positioned_lights_delta"], 0)
            self.assertEqual(payload["scene_changes"]["directional_lights_delta"], 0)
            self.assertEqual(payload["scene_changes"]["lights_with_temperature_delta"], 0)
            self.assertFalse(payload["scene_changes"]["light_temperature_range_changed"])
            self.assertTrue(payload["scene_changes"]["light_colors_changed"])
            self.assertTrue(payload["scene_changes"]["light_ids_changed"])
            self.assertEqual(payload["scene_changes"]["light_ids_count_delta"], 0)
            self.assertIn("position", payload["object_changes"]["object.tree"]["field_changes"])
            self.assertIn("state", payload["object_changes"]["object.tree"]["field_changes"])
            self.assertIn("visibility", payload["object_changes"]["object.tree"]["field_changes"])

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
            assumptions_path = tmp_dir / "normalized-scene.assumptions.json"

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
                        "    state: ' TRANSITIONING '",
                        "    visibility: ' HIDDEN '",
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
                        "  framing_intent: ' SUBJECT-FOCUSED '",
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
                        "    color: ' ACCENT '",
                        "  - light_id: light.a",
                        "    intensity: 2",
                        "    position:",
                        "      x: 1",
                        "      y: 2",
                        "      z: -1",
                        "    color: ' WARM '",
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
                "--assumptions",
                str(assumptions_path),
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
            self.assertEqual(payload["assumptions_output"], str(assumptions_path))
            self.assertEqual(payload["assumptions_format"], "json")
            self.assertTrue(report_path.exists())
            self.assertTrue(assumptions_path.exists())

            report_document = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_document["report_version"], 1)
            self.assertEqual(report_document["spec"], str(source_path))
            self.assertEqual(report_document["spec_output"], str(normalized_path))
            self.assertFalse(report_document["source_validation"]["is_valid"])
            self.assertTrue(report_document["normalized_validation"]["is_valid"])
            self.assertEqual(report_document["normalized_document"]["reference_frame"], "world")

            assumptions_document = json.loads(assumptions_path.read_text(encoding="utf-8"))
            self.assertEqual(assumptions_document["manifest_version"], 1)
            self.assertEqual(assumptions_document["spec"], str(source_path))
            self.assertEqual(assumptions_document["spec_output"], str(normalized_path))
            self.assertEqual(assumptions_document["scene_id"], "courtyard.scene")
            self.assertGreaterEqual(assumptions_document["summary"]["assumption_count"], 6)
            self.assertTrue(any(item["kind"] == "alias_resolved" for item in assumptions_document["assumptions"]))

            inspect_payload = self._run_json(repo_root, "vrwif-inspect", str(normalized_path), "--json")
            self.assertEqual(inspect_payload["reference_frame"], "world")
            self.assertEqual(inspect_payload["objects"][0]["object_id"], "object.a")
            self.assertEqual(inspect_payload["objects"][1]["appearance_class"], "statue")
            self.assertEqual(inspect_payload["objects"][1]["object_groups"], ["alpha", "beta"])
            self.assertEqual(inspect_payload["objects"][1]["state"], "transitioning")
            self.assertEqual(inspect_payload["objects"][1]["visibility"], "hidden")
            self.assertEqual(inspect_payload["objects"][1]["trajectory"][0]["offset_seconds"], 0.0)
            self.assertEqual(inspect_payload["camera"]["camera_id"], "cam.main")
            self.assertEqual(inspect_payload["camera"]["framing_intent"], "subject-focused")
            self.assertEqual(inspect_payload["lighting"][0]["light_id"], "light.a")
            self.assertEqual(inspect_payload["lighting"][0]["color"], "warm")

    def test_vrwif_batch_normalize_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first.yaml"
            second_path = tmp_dir / "second.yaml"
            output_dir = tmp_dir / "normalized"
            report_dir = tmp_dir / "reports"
            assumptions_dir = tmp_dir / "assumptions"
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
                "--assumptions-dir",
                str(assumptions_dir),
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
            self.assertEqual(payload["assumptions_dir"], str(assumptions_dir))
            self.assertGreaterEqual(payload["total_assumption_count"], 1)
            self.assertTrue((output_dir / "first.normalized.yaml").exists())
            self.assertTrue((output_dir / "second.normalized.yaml").exists())
            self.assertTrue((report_dir / "first.normalized.report.json").exists())
            self.assertTrue((report_dir / "second.normalized.report.json").exists())
            self.assertTrue((assumptions_dir / "first.normalized.assumptions.json").exists())
            self.assertTrue((assumptions_dir / "second.normalized.assumptions.json").exists())
            self.assertTrue(report_path.exists())

    def test_vrwif_batch_normalize_analyze_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first.yaml"
            second_path = tmp_dir / "second.yaml"
            output_dir = tmp_dir / "normalized"
            report_path = tmp_dir / "vrwif-batch-normalize-report.json"
            analysis_path = tmp_dir / "vrwif-batch-normalize-analysis.json"

            first_path.write_text(
                "\n".join(
                    [
                        "scene_id: first.scene",
                        "reference_frame: SCENE",
                        "unexpected_flag: true",
                        "objects:",
                        "  - object_id: object.first",
                        "    class: prop",
                        "    object_groups:",
                        "      - zeta",
                        "      - alpha",
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

            normalize_payload = self._run_json(
                repo_root,
                "vrwif-batch-normalize",
                str(first_path),
                str(second_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(report_path),
                "--json",
            )
            self.assertTrue(normalize_payload["is_valid"], normalize_payload)
            self.assertTrue(report_path.exists())

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-normalize-analyze",
                str(report_path),
                "--output",
                str(analysis_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["specs_processed"], 2)
            self.assertEqual(analysis_payload["normalized_count"], 2)
            self.assertEqual(analysis_payload["summary"]["specs_with_assumptions"], 2)
            self.assertEqual(analysis_payload["summary"]["specs_with_source_errors"], 1)
            self.assertEqual(
                analysis_payload["normalization_action_frequencies"][0]["specs_affected"],
                2,
            )
            self.assertEqual(
                analysis_payload["normalization_action_frequencies"][0]["action"],
                "inserted_vrwif_version",
            )
            self.assertIn(
                "resolved_class_aliases",
                [item["action"] for item in analysis_payload["normalization_action_frequencies"]],
            )
            self.assertIn(
                "dropped_unknown_top_level_fields",
                [item["action"] for item in analysis_payload["normalization_action_frequencies"]],
            )
            self.assertGreaterEqual(len(analysis_payload["source_error_frequencies"]), 1)
            self.assertEqual(analysis_payload["top_specs_by_assumption_count"][0]["spec"], str(first_path))
            self.assertTrue(analysis_path.exists())

    def test_vrwif_batch_normalize_review_specs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            first_path = tmp_dir / "first.yaml"
            second_path = tmp_dir / "second.yaml"
            output_dir = tmp_dir / "normalized"
            review_path = tmp_dir / "vrwif-batch-normalize-review.json"

            first_path.write_text(
                "\n".join(
                    [
                        "scene_id: first.scene",
                        "reference_frame: SCENE",
                        "objects:",
                        "  - object_id: object.first",
                        "    class: prop",
                        "    object_groups:",
                        "      - beta",
                        "      - alpha",
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
                "vrwif-batch-normalize-review",
                str(first_path),
                str(second_path),
                "--output-dir",
                str(output_dir),
                "--output",
                str(review_path),
                "--json",
            )
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["specs_processed"], 2)
            self.assertEqual(payload["normalized_count"], 2)
            self.assertIn("normalize_report", payload)
            self.assertIn("analysis", payload)
            self.assertEqual(payload["analysis"]["specs_processed"], 2)
            self.assertTrue((output_dir / "first.normalized.yaml").exists())
            self.assertTrue(review_path.exists())

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
                        "    state: idle",
                        "    visibility: visible",
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
                        "  framing_intent: centered-medium",
                        "lighting:",
                        "  - light_id: light.a",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                        "    color: warm",
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
                        "    state: active",
                        "    visibility: occluded",
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
                        "  framing_intent: detail-close",
                        "lighting:",
                        "  - light_id: light.a",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                        "    color: cool",
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
                        "    state: idle",
                        "    visibility: hidden",
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
                        "  framing_intent: establishing",
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
                        "    state: idle",
                        "    visibility: hidden",
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
                        "  framing_intent: establishing",
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
            self.assertEqual(analysis_payload["scene_change_summary"]["object_ids_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_changed_pairs"], 2)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_distance_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_distance_delta"], 1.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_distance_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_distance_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_distance_delta"], 0.12018611938930146)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_duration_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_duration_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_path_length_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_path_length_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_displacement_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_displacement_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_speed_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_speed_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_peak_speed_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_peak_speed_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_speed_standard_deviation_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_speed_standard_deviation_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_acceleration_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_acceleration_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_straightness_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_straightness_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_angle_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_angle_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_peak_turn_angle_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_peak_turn_angle_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_turn_angle_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_turn_angle_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_angle_standard_deviation_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_angle_standard_deviation_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_point_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_point_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_duration_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_duration_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_duration_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_path_length_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_path_length_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_path_length_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_displacement_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_displacement_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_displacement_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_speed_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_speed_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_speed_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_peak_speed_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_peak_speed_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_peak_speed_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_speed_standard_deviation_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_speed_standard_deviation_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_speed_standard_deviation_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_straightness_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_straightness_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_straightness_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_angle_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_angle_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_angle_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["framing_intent_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_id_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_has_trajectory_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["appearance_classes_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_appearance_classes_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_appearance_classes_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_states_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_visibilities_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["lighting_present_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_intensity_total_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_light_intensity_delta"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_intensity_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_positioned_light_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_directional_light_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_temperature_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_temperature_range_changed_pairs"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_colors_changed_pairs"], 1)
            self.assertEqual(analysis_payload["objects_changed_in_all_changed_pairs"], [])
            self.assertEqual(analysis_payload["analysis_input"], str(diff_report_path))
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_light_placement_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-light-scene.yaml"
            right_path = tmp_dir / "right-light-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.scene",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                        "    color: warm",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.scene",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.5",
                        "    intensity: 1.0",
                        "    color: warm",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["positioned_lights_delta"], -1)
            self.assertEqual(payload["scene_changes"]["directional_lights_delta"], 1)

    def test_vrwif_diff_reports_camera_distance_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-scene.yaml"
            right_path = tmp_dir / "right-camera-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 2.0",
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

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_distance_from_origin_delta"], 1.3098582948312)

    def test_vrwif_diff_reports_object_distance_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-distance-scene.yaml"
            right_path = tmp_dir / "right-object-distance-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 3.0",
                        "      y: 4.0",
                        "      z: 0.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 2.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_distance_from_origin_total_delta"], 6.0)
            self.assertTrue(payload["scene_changes"]["object_distance_from_origin_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_distance_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-distance.yaml"
            right_path = tmp_dir / "right-batch-object-distance.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-distance-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-distance-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-distance",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 3.0",
                        "      y: 4.0",
                        "      z: 0.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 2.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_distance_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_distance_delta"], 6.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_distance_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_duration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-duration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-duration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.5",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.5",
                        "        position:",
                        "          x: 0.0",
                        "          y: 2.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_duration_total_delta"], 3.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_duration_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_duration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.5",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.5",
                        "        position:",
                        "          x: 0.0",
                        "          y: 2.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_duration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_duration_delta"], 3.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_duration_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_path_length_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-path-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-path-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-path-length",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-path-length",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_path_length_total_delta"], 6.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_path_length_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_path_length_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-path.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-path.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-path-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-path-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-path",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-path",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_path_length_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_path_length_delta"], 6.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_path_length_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_displacement_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-displacement-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-displacement-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_displacement_total_delta"], 6.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_displacement_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_displacement_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-displacement.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-displacement.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-displacement-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-displacement-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_displacement_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_displacement_delta"], 6.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_displacement_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_average_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-speed-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-speed-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_average_speed_total_delta"], 6.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_average_speed_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_average_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-speed.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-speed.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-speed-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-speed-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 3.0",
                        "          z: 4.0",
                        "  - object_id: object.two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 1.0",
                        "          z: 2.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_speed_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_speed_delta"], 6.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_speed_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_peak_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-peak-speed-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-peak-speed-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_peak_speed_total_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_peak_speed_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_peak_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-peak-speed.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-peak-speed.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-speed-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-speed-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_peak_speed_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_peak_speed_delta"], 2.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_peak_speed_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_speed_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-speed-standard-deviation-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-speed-standard-deviation-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_speed_standard_deviation_total_delta"], 1.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_speed_standard_deviation_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_speed_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-speed-standard-deviation.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-speed-standard-deviation.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-speed-standard-deviation-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-speed-standard-deviation-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_speed_standard_deviation_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_speed_standard_deviation_delta"], 1.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_speed_standard_deviation_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_average_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-average-acceleration-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-average-acceleration-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_average_acceleration_total_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_average_acceleration_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_average_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-average-acceleration.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-average-acceleration.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-average-acceleration-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-average-acceleration-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_acceleration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_acceleration_delta"], 2.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_acceleration_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_peak_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-peak-acceleration-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-peak-acceleration-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_peak_acceleration_total_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_peak_acceleration_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_peak_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-peak-acceleration.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-peak-acceleration.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-acceleration-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-acceleration-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 2.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 1.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_peak_acceleration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_peak_acceleration_delta"], 2.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_peak_acceleration_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_straightness_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-straightness-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-straightness-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_straightness_total_delta"], -0.2857142857142857)
            self.assertTrue(payload["scene_changes"]["object_trajectory_straightness_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_straightness_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-straightness.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-straightness.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-straightness-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-straightness-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_straightness_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_straightness_delta"], -0.2857142857142857)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_straightness_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_turn_angle_total_degrees_delta"], 90.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_turn_angle_range_degrees_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_angle_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_peak_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_peak_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_peak_turn_angle_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_count_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_turn_angle_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_angle_standard_deviation_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_angle_standard_deviation_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_angle_standard_deviation_range_changed_pairs"], 0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_peak_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-peak-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-peak-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_peak_turn_angle_total_degrees_delta"], 90.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_peak_turn_angle_range_degrees_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_peak_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-peak-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-peak-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-peak-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_peak_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_peak_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_peak_turn_angle_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_turn_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-turn-count-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-turn-count-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["object_trajectory_turn_count_total_delta"], 2)
            self.assertTrue(payload["scene_changes"]["object_trajectory_turn_count_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_turn_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-turn-count.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-turn-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_count_delta"], 2)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_count_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_turn_angle_range_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_angle_standard_deviation_delta"], 0)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_angle_standard_deviation_delta_degrees"], 0.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_angle_standard_deviation_range_changed_pairs"], 0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_average_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-average-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-average-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_average_turn_angle_total_degrees_delta"], 90.0)
            self.assertTrue(payload["scene_changes"]["object_trajectory_average_turn_angle_range_degrees_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_average_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-average-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-average-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-average-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-average-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 0.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 3.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 6.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_average_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_average_turn_angle_delta_degrees"], 90.0)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_average_turn_angle_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_object_trajectory_turn_angle_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-trajectory-turn-angle-standard-deviation-scene.yaml"
            right_path = tmp_dir / "right-object-trajectory-turn-angle-standard-deviation-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object.trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 5.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["object_trajectory_turn_angle_standard_deviation_total_degrees_delta"], 22.5)
            self.assertTrue(payload["scene_changes"]["object_trajectory_turn_angle_standard_deviation_range_degrees_changed"])

    def test_vrwif_batch_diff_analysis_reports_object_trajectory_turn_angle_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-trajectory-turn-angle-standard-deviation.yaml"
            right_path = tmp_dir / "right-batch-object-trajectory-turn-angle-standard-deviation.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-angle-standard-deviation-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-trajectory-turn-angle-standard-deviation-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 4.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "    trajectory:",
                        "      - offset_seconds: 0.0",
                        "        position:",
                        "          x: 0.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 1.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 0.0",
                        "          z: 0.0",
                        "      - offset_seconds: 2.0",
                        "        position:",
                        "          x: 4.0",
                        "          y: 4.0",
                        "          z: 0.0",
                        "      - offset_seconds: 3.0",
                        "        position:",
                        "          x: 5.0",
                        "          y: 5.0",
                        "          z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_trajectory_turn_angle_standard_deviation_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_object_trajectory_turn_angle_standard_deviation_delta_degrees"], 22.5)
            self.assertEqual(analysis_payload["scene_change_summary"]["trajectory_turn_angle_standard_deviation_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_inspect_reports_camera_trajectory_duration(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "inspect-camera-trajectory-scene.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-duration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -3.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-inspect", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertTrue(payload["scene_summary"]["camera_has_trajectory"])
            self.assertEqual(payload["scene_summary"]["camera_trajectory_point_count"], 2)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_duration"], 2.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_path_length"], 1.118033988749895)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_displacement"], 1.118033988749895)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_average_speed"], 0.5590169943749475)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_peak_speed"], 0.5590169943749475)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_speed_standard_deviation"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_average_acceleration"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_peak_acceleration"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_straightness"], 1.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_turn_angle_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_peak_turn_angle_degrees"], 0.0)
            self.assertEqual(payload["scene_summary"]["camera_trajectory_turn_count"], 0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_average_turn_angle_degrees"], 0.0)
            self.assertAlmostEqual(payload["scene_summary"]["camera_trajectory_turn_angle_standard_deviation_degrees"], 0.0)

    def test_vrwif_diff_reports_camera_trajectory_duration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -3.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.5",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -3.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_duration_delta"], 2.5)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-presence-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-presence-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["scene_changes"]["camera_has_trajectory_changed"])
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])
            self.assertEqual(payload["scene_changes"]["camera_trajectory_point_count_delta"], 2)

    def test_vrwif_diff_reports_camera_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-id-scene.yaml"
            right_path = tmp_dir / "right-camera-id-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.id-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.alpha",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.id-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.beta",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["scene_changes"]["camera_id_changed"])
            self.assertTrue(payload["scene_changes"]["camera_changed"])
            self.assertFalse(payload["scene_changes"]["camera_has_trajectory_changed"])

    def test_vrwif_diff_reports_object_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-count-scene.yaml"
            right_path = tmp_dir / "right-object-count-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.extra-one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.extra-two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 2.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["object_count_delta"], 2)
            self.assertEqual(payload["change_summary"]["added_objects"], 2)

    def test_vrwif_diff_reports_object_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-object-ids-scene.yaml"
            right_path = tmp_dir / "right-object-ids-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: object-ids-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: object-ids-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.beta",
                        "    object_groups:",
                        "      - set",
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

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["scene_changes"]["object_ids_changed"])
            self.assertEqual(payload["scene_changes"]["object_ids_count_delta"], 0)
            self.assertEqual(payload["change_summary"]["added_objects"], 1)
            self.assertEqual(payload["change_summary"]["removed_objects"], 1)

    def test_vrwif_diff_reports_camera_trajectory_path_length_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-path-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-path-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-path-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-path-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_path_length_delta"], 4.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_average_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-speed-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-speed-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-speed-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-speed-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_speed_delta"], 4.5)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_peak_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-peak-speed-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-peak-speed-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-speed-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-speed-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_peak_speed_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_speed_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-speed-standard-deviation-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-speed-standard-deviation-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-speed-standard-deviation-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-speed-standard-deviation-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_speed_standard_deviation_delta"], 1.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_average_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-average-acceleration-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-average-acceleration-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-acceleration-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-acceleration-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_acceleration_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_peak_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-peak-acceleration-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-peak-acceleration-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-acceleration-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-acceleration-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_peak_acceleration_delta"], 2.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_displacement_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-displacement-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-displacement-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-displacement-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-displacement-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_displacement_delta"], 4.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_straightness_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-straightness-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-straightness-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-straightness-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-straightness-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_straightness_delta"], -0.2857142857142857)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-angle-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-angle-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_turn_angle_degrees_delta"], 90.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_peak_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-peak-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-peak-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-turn-angle-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-peak-turn-angle-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_peak_turn_angle_degrees_delta"], 90.0)

    def test_vrwif_diff_reports_camera_trajectory_average_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-average-turn-angle-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-average-turn-angle-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_average_turn_angle_degrees_delta"], 90.0)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_turn_angle_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-turn-angle-standard-deviation-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-turn-angle-standard-deviation-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 6.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertAlmostEqual(payload["scene_changes"]["camera_trajectory_turn_angle_standard_deviation_degrees_delta"], 22.5)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_turn_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-turn-count-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-turn-count-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-turn-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["camera_trajectory_turn_count_delta"], 2)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_diff_reports_camera_trajectory_point_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-trajectory-point-count-scene.yaml"
            right_path = tmp_dir / "right-camera-trajectory-point-count-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-point-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.trajectory-point-count-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["camera_trajectory_point_count_delta"], 2)
            self.assertTrue(payload["scene_changes"]["camera_trajectory_changed"])

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_duration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -3.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.5",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -3.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_duration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_duration_delta"], 2.5)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-presence.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-presence.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-presence-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-presence-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_has_trajectory_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-id.yaml"
            right_path = tmp_dir / "right-batch-camera-id.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-id-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-id-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-id",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.alpha",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-id",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.beta",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_id_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_object_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-count.yaml"
            right_path = tmp_dir / "right-batch-object-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.extra-one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.extra-two",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 2.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_count_delta"], 2)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_object_id_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-ids.yaml"
            right_path = tmp_dir / "right-batch-object-ids.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-ids-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-ids-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-ids",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-ids",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.beta",
                        "    object_groups:",
                        "      - set",
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

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_ids_count_delta"], 0)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_light_ids_count_delta"], 0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_tracks_object_groups_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-groups-count.yaml"
            right_path = tmp_dir / "right-batch-object-groups-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-groups-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-groups-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-groups-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-groups-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
                        "      - foreground",
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

            diff_payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(diff_payload["scene_changes"]["object_groups_changed"])
            self.assertEqual(diff_payload["scene_changes"]["object_groups_count_delta"], 1)
            self.assertEqual(diff_payload["scene_changes"]["object_count_delta"], 0)

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_groups_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_groups_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_groups_count_delta"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_tracks_object_ids_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-object-ids-count.yaml"
            right_path = tmp_dir / "right-batch-object-ids-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-object-ids-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-object-ids-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-ids-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.object-ids-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.alpha",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.beta",
                        "    object_groups:",
                        "      - set",
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

            diff_payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(diff_payload["scene_changes"]["object_ids_changed"])
            self.assertEqual(diff_payload["scene_changes"]["object_ids_count_delta"], 1)
            self.assertEqual(diff_payload["scene_changes"]["object_count_delta"], 1)

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["object_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_object_ids_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_object_ids_count_delta"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_tracks_light_ids_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-light-ids-count.yaml"
            right_path = tmp_dir / "right-batch-light-ids-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-light-ids-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-light-ids-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.light-ids-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: key",
                        "    kind: point",
                        "    intensity: 1.0",
                        "    position:",
                        "      x: 2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    color: warm",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.light-ids-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: key",
                        "    kind: point",
                        "    intensity: 1.0",
                        "    position:",
                        "      x: 2.0",
                        "      y: 3.0",
                        "      z: -1.0",
                        "    color: warm",
                        "  - light_id: fill",
                        "    kind: directional",
                        "    intensity: 0.5",
                        "    direction:",
                        "      x: -1.0",
                        "      y: -1.0",
                        "      z: 0.0",
                        "    color: cool",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(diff_payload["scene_changes"]["light_ids_changed"])
            self.assertEqual(diff_payload["scene_changes"]["light_ids_count_delta"], 1)
            self.assertEqual(diff_payload["scene_changes"]["light_count_delta"], 1)

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_ids_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_ids_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_light_ids_count_delta"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_tracks_appearance_classes_count_delta(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-appearance-classes-count.yaml"
            right_path = tmp_dir / "right-batch-appearance-classes-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-appearance-classes-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-appearance-classes-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.appearance-classes-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.appearance-classes-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "  - object_id: object.marker",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: marker",
                        "    position:",
                        "      x: 1.0",
                        "      y: 0.0",
                        "      z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(diff_payload["scene_changes"]["appearance_classes_changed"])
            self.assertEqual(diff_payload["scene_changes"]["appearance_classes_count_delta"], 1)
            self.assertEqual(diff_payload["scene_changes"]["object_count_delta"], 1)

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["appearance_classes_changed_pairs"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_appearance_classes_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_appearance_classes_count_delta"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_path_length_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-path.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-path.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-path-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-path-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-path",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-path",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_path_length_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_path_length_delta"], 4.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_average_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-speed.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-speed.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-speed-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-speed-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_speed_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_speed_delta"], 4.5)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_peak_speed_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-peak-speed.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-peak-speed.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-speed-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-speed-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-speed",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_peak_speed_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_peak_speed_delta"], 2.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_speed_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-speed-standard-deviation.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-speed-standard-deviation.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-speed-standard-deviation-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-speed-standard-deviation-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-speed-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_speed_standard_deviation_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_speed_standard_deviation_delta"], 1.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_average_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-average-acceleration.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-average-acceleration.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-average-acceleration-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-average-acceleration-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_acceleration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_acceleration_delta"], 2.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_peak_acceleration_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-peak-acceleration.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-peak-acceleration.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-acceleration-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-acceleration-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-acceleration",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_peak_acceleration_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_peak_acceleration_delta"], 2.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_displacement_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-displacement.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-displacement.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-displacement-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-displacement-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-displacement",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 4.0",
                        "        z: 0.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_displacement_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_displacement_delta"], 4.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_straightness_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-straightness.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-straightness.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-straightness-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-straightness-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-straightness",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_straightness_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_straightness_delta"], -0.2857142857142857)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_angle_delta_degrees"], 90.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_peak_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-peak-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-peak-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-peak-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-peak-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_peak_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_peak_turn_angle_delta_degrees"], 90.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_turn_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-turn-count.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-turn-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_count_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_count_delta"], 2)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_point_count_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-point-count.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-point-count.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-point-count-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-point-count-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-point-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-point-count",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.moving",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 1.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 2.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_point_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_point_delta"], 2)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_average_turn_angle_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-average-turn-angle.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-average-turn-angle.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-average-turn-angle-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-average-turn-angle-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 1.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-average-turn-angle",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 3.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 6.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_average_turn_angle_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_average_turn_angle_delta_degrees"], 90.0)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_camera_trajectory_turn_angle_standard_deviation_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-trajectory-turn-angle-standard-deviation.yaml"
            right_path = tmp_dir / "right-batch-camera-trajectory-turn-angle-standard-deviation.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-angle-standard-deviation-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-trajectory-turn-angle-standard-deviation-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 5.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-trajectory-turn-angle-standard-deviation",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.main",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
                        "    z: -4.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "    z: 1.0",
                        "  trajectory:",
                        "    - offset_seconds: 0.0",
                        "      position:",
                        "        x: 0.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 1.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 1.0",
                        "        z: -4.0",
                        "    - offset_seconds: 2.0",
                        "      position:",
                        "        x: 4.0",
                        "        y: 5.0",
                        "        z: -4.0",
                        "    - offset_seconds: 3.0",
                        "      position:",
                        "        x: 5.0",
                        "        y: 6.0",
                        "        z: -4.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_camera_trajectory_turn_angle_standard_deviation_delta"], 1)
            self.assertAlmostEqual(analysis_payload["scene_change_summary"]["total_camera_trajectory_turn_angle_standard_deviation_delta_degrees"], 22.5)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_light_temperature_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-temperature-scene.yaml"
            right_path = tmp_dir / "right-temperature-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.temperature",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                        "    temperature_kelvin: 3200",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.temperature",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: -1.0",
                        "    intensity: 1.0",
                        "    temperature_kelvin: 5600",
                        "  - light_id: light.fill",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.0",
                        "    intensity: 0.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["lights_with_temperature_delta"], 0)
            self.assertTrue(payload["scene_changes"]["light_temperature_range_changed"])

    def test_vrwif_diff_reports_light_intensity_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-intensity-scene.yaml"
            right_path = tmp_dir / "right-intensity-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.intensity",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
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
                        "scene_id: lighting.intensity",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.key",
                        "    position:",
                        "      x: 0.0",
                        "      y: 1.0",
                        "      z: -1.0",
                        "    intensity: 1.8",
                        "  - light_id: light.fill",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.5",
                        "    intensity: 0.4",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertEqual(payload["scene_changes"]["light_intensity_total_delta"], 1.2000000000000002)
            self.assertTrue(payload["scene_changes"]["light_intensity_range_changed"])

    def test_vrwif_batch_diff_analysis_reports_light_intensity_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-intensity.yaml"
            right_path = tmp_dir / "right-batch-intensity.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-intensity-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-intensity-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.intensity",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.one",
                        "    position:",
                        "      x: -1.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    intensity: 1.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.intensity",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.one",
                        "    position:",
                        "      x: -1.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    intensity: 1.8",
                        "  - light_id: light.two",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.5",
                        "    intensity: 0.4",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_intensity_total_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_light_intensity_delta"], 1.2000000000000002)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_intensity_range_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_batch_diff_analysis_reports_light_temperature_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-temperature.yaml"
            right_path = tmp_dir / "right-batch-temperature.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-temperature-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-temperature-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.temperature",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.one",
                        "    position:",
                        "      x: -1.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    intensity: 1.0",
                        "    temperature_kelvin: 3200",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.temperature",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.one",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: light.one",
                        "    position:",
                        "      x: -1.0",
                        "      y: 1.0",
                        "      z: 0.0",
                        "    intensity: 1.0",
                        "    temperature_kelvin: 5600",
                        "  - light_id: light.two",
                        "    direction:",
                        "      x: 0.0",
                        "      y: -1.0",
                        "      z: 0.5",
                        "    intensity: 0.7",
                        "    temperature_kelvin: 4800",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["pairs_with_light_temperature_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["total_lights_with_temperature_delta"], 1)
            self.assertEqual(analysis_payload["scene_change_summary"]["light_temperature_range_changed_pairs"], 1)
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
                        "    state: broken",
                        "    visibility: unknown",
                        "camera:",
                        "  camera_id: ''",
                        "  position:",
                        "    x: 0.0",
                        "    y: nope",
                        "    z: -1.0",
                        "  orientation:",
                        "    x: 0.0",
                        "    y: 0.0",
                        "  framing_intent: impossible",
                        "lighting:",
                        "  - light_id: ''",
                        "    color: impossible",
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
            self.assertIn("objects[0].state must be one of: idle, active, transitioning", payload["errors"])
            self.assertIn("objects[0].visibility must be one of: visible, occluded, hidden", payload["errors"])
            self.assertIn("camera.camera_id must be a non-empty string", payload["errors"])
            self.assertIn("camera.position.y must be a finite number", payload["errors"])
            self.assertIn("camera.orientation.z must be a finite number", payload["errors"])
            self.assertIn(
                "camera.framing_intent must be one of: establishing, centered-medium, subject-focused, detail-close",
                payload["errors"],
            )
            self.assertIn("lighting[0].light_id must be a non-empty string", payload["errors"])
            self.assertIn("lighting[0].color must be one of: warm, neutral, cool, accent", payload["errors"])
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
    def test_vrwif_diff_reports_camera_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-camera-presence-scene.yaml"
            right_path = tmp_dir / "right-camera-presence-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: camera.presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.present",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["scene_changes"]["camera_present_changed"])
            self.assertTrue(payload["scene_changes"]["camera_changed"])
            self.assertFalse(payload["scene_changes"]["camera_id_changed"])

    def test_vrwif_batch_diff_analysis_reports_camera_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-camera-presence.yaml"
            right_path = tmp_dir / "right-batch-camera-presence.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-camera-presence-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-camera-presence-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.camera-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "camera:",
                        "  camera_id: cam.present",
                        "  position:",
                        "    x: 0.0",
                        "    y: 1.0",
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
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["camera_present_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())

    def test_vrwif_diff_reports_lighting_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-lighting-presence-scene.yaml"
            right_path = tmp_dir / "right-lighting-presence-scene.yaml"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: lighting.presence-diff",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: key.light",
                        "    intensity: 1.0",
                        "    color: warm",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: 3.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "vrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["scene_changes"]["lighting_present_changed"])
            self.assertEqual(payload["scene_changes"]["light_count_delta"], 1)

    def test_vrwif_batch_diff_analysis_reports_lighting_presence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left-batch-lighting-presence.yaml"
            right_path = tmp_dir / "right-batch-lighting-presence.yaml"
            diff_report_path = tmp_dir / "vrwif-batch-lighting-presence-diff.json"
            analysis_report_path = tmp_dir / "vrwif-batch-lighting-presence-analysis.json"

            left_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.lighting-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
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
            right_path.write_text(
                "\n".join(
                    [
                        "scene_id: batch.lighting-presence",
                        "reference_frame: scene",
                        "objects:",
                        "  - object_id: object.anchor",
                        "    object_groups:",
                        "      - set",
                        "    appearance_class: prop",
                        "    position:",
                        "      x: 0.0",
                        "      y: 0.0",
                        "      z: 0.0",
                        "lighting:",
                        "  - light_id: key.light",
                        "    intensity: 1.0",
                        "    color: warm",
                        "    position:",
                        "      x: 1.0",
                        "      y: 2.0",
                        "      z: 3.0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diff_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff",
                "--left",
                str(left_path),
                "--right",
                str(right_path),
                "--output",
                str(diff_report_path),
                "--json",
            )
            self.assertTrue(diff_payload["is_valid"], diff_payload)

            analysis_payload = self._run_json(
                repo_root,
                "vrwif-batch-diff-analyze",
                str(diff_report_path),
                "--output",
                str(analysis_report_path),
                "--json",
            )
            self.assertTrue(analysis_payload["is_valid"], analysis_payload)
            self.assertEqual(analysis_payload["scene_change_summary"]["lighting_present_changed_pairs"], 1)
            self.assertTrue(analysis_report_path.exists())


if __name__ == "__main__":
    unittest.main()
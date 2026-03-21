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
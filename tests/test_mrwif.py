from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MRWIFValidationTest(unittest.TestCase):
    def test_mrwif_validate_spec_accepts_minimal_correspondence_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "correspondence.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "mrwif_version: 1",
                        "correspondence_id: launch.identity-01",
                        "title: Launch identity bridge",
                        "linked_artifacts:",
                        "  - realm: rwif",
                        "    artifact_id: concept.launch-01",
                        "    role: semantic-anchor",
                        "  - realm: arwif",
                        "    artifact_id: audio.launch-01",
                        "    role: sonic-variant",
                        "  - realm: vrwif",
                        "    artifact_id: scene.launch-01",
                        "    role: visual-variant",
                        "intent_mappings:",
                        "  - mapping_id: intent.warm-urgent",
                        "    semantic_descriptors:",
                        "      - warm",
                        "      - urgent",
                        "    target_realm: arwif",
                        "    target_descriptors:",
                        "      - softer-attack",
                        "      - faster-tempo",
                        "    confidence: 0.8",
                        "interpretation_records:",
                        "  - record_id: interp.audio-01",
                        "    artifact_id: audio.launch-01",
                        "    inferred_descriptors:",
                        "      - warm",
                        "      - tense",
                        "    confidence: 0.6",
                        "    ambiguity_notes:",
                        "      - shares traits with triumphant",
                        "revision_traces:",
                        "  - revision_id: rev.01",
                        "    requested_changes:",
                        "      - increase tension",
                        "    applied_changes:",
                        "      - sharpen transient",
                        "    affected_realms:",
                        "      - arwif",
                        "      - vrwif",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "mrwif-validate-spec", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["stats"]["correspondence_id"], "launch.identity-01")
            self.assertEqual(payload["stats"]["linked_artifact_count"], 3)
            self.assertEqual(payload["stats"]["linked_artifact_realms"], ["arwif", "rwif", "vrwif"])
            self.assertEqual(payload["stats"]["semantic_descriptors"], ["urgent", "warm"])
            self.assertEqual(payload["stats"]["interpretation_record_count"], 1)
            self.assertEqual(payload["stats"]["ambiguity_note_count"], 1)
            self.assertEqual(payload["stats"]["revision_trace_count"], 1)
            self.assertEqual(payload["normalized_document"]["linked_artifacts"][0]["artifact_id"], "concept.launch-01")

    def test_mrwif_validate_spec_rejects_invalid_correspondence_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "invalid-correspondence.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "mrwif_version: 2",
                        "correspondence_id: ''",
                        "linked_artifacts:",
                        "  - realm: ''",
                        "    artifact_id: ''",
                        "intent_mappings:",
                        "  - mapping_id: ''",
                        "    semantic_descriptors:",
                        "      - ok",
                        "      - ''",
                        "    target_realm: ''",
                        "    target_descriptors: broken",
                        "    confidence: 1.2",
                        "interpretation_records:",
                        "  - record_id: ''",
                        "    artifact_id: ''",
                        "    inferred_descriptors: nope",
                        "    ambiguity_notes:",
                        "      - ''",
                        "    confidence: -0.1",
                        "revision_traces:",
                        "  - revision_id: ''",
                        "    requested_changes: bad",
                        "    applied_changes:",
                        "      - ''",
                        "    affected_realms:",
                        "      - ''",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "mrwif-validate-spec", str(spec_path), "--json", allow_failure=True)
            self.assertFalse(payload["is_valid"])
            self.assertIn("mrwif_version must be 1", payload["errors"])
            self.assertIn("correspondence_id must be a non-empty string", payload["errors"])
            self.assertIn("linked_artifacts[0].realm must be a non-empty string", payload["errors"])
            self.assertIn("linked_artifacts[0].artifact_id must be a non-empty string", payload["errors"])
            self.assertIn("intent_mappings[0].mapping_id must be a non-empty string", payload["errors"])
            self.assertIn("intent_mappings[0].semantic_descriptors[1] must be a non-empty string", payload["errors"])
            self.assertIn("intent_mappings[0].target_realm must be a non-empty string", payload["errors"])
            self.assertIn("intent_mappings[0].target_descriptors must be a list", payload["errors"])
            self.assertIn("intent_mappings[0].confidence must be a finite number between 0.0 and 1.0", payload["errors"])
            self.assertIn("interpretation_records[0].record_id must be a non-empty string", payload["errors"])
            self.assertIn("interpretation_records[0].artifact_id must be a non-empty string", payload["errors"])
            self.assertIn("interpretation_records[0].inferred_descriptors must be a list", payload["errors"])
            self.assertIn("interpretation_records[0].ambiguity_notes[0] must be a non-empty string", payload["errors"])
            self.assertIn("interpretation_records[0].confidence must be a finite number between 0.0 and 1.0", payload["errors"])
            self.assertIn("revision_traces[0].revision_id must be a non-empty string", payload["errors"])
            self.assertIn("revision_traces[0].requested_changes must be a list", payload["errors"])
            self.assertIn("revision_traces[0].applied_changes[0] must be a non-empty string", payload["errors"])
            self.assertIn("revision_traces[0].affected_realms[0] must be a non-empty string", payload["errors"])

    def test_mrwif_inspect_reports_correspondence_summary(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            spec_path = tmp_dir / "inspect-correspondence.yaml"
            spec_path.write_text(
                "\n".join(
                    [
                        "correspondence_id: scene-review-01",
                        "description: Links one review concept across media.",
                        "linked_artifacts:",
                        "  - realm: rwif",
                        "    artifact_id: memory.scene-review",
                        "  - realm: vrwif",
                        "    artifact_id: visual.scene-review",
                        "intent_mappings:",
                        "  - mapping_id: intent.calm",
                        "    semantic_descriptors:",
                        "      - calm",
                        "      - focused",
                        "    target_realm: vrwif",
                        "    target_descriptors:",
                        "      - softer-contrast",
                        "interpretation_records:",
                        "  - record_id: interp.visual-01",
                        "    artifact_id: visual.scene-review",
                        "    inferred_descriptors:",
                        "      - calm",
                        "    ambiguity_notes:",
                        "      - could also read as reserved",
                        "revision_traces:",
                        "  - revision_id: rev.visual-01",
                        "    requested_changes:",
                        "      - reduce urgency",
                        "    applied_changes:",
                        "      - reduce brightness contrast",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "mrwif-inspect", str(spec_path), "--json")
            self.assertTrue(payload["is_valid"], payload)
            self.assertEqual(payload["correspondence_id"], "scene-review-01")
            self.assertEqual(payload["linked_artifacts"][1]["artifact_id"], "visual.scene-review")
            self.assertEqual(payload["intent_mappings"][0]["target_realm"], "vrwif")
            self.assertEqual(payload["interpretation_records"][0]["ambiguity_notes"], ["could also read as reserved"])
            self.assertEqual(payload["revision_traces"][0]["requested_changes"], ["reduce urgency"])
            self.assertEqual(payload["correspondence_summary"]["linked_artifact_count"], 2)
            self.assertEqual(payload["correspondence_summary"]["semantic_descriptors"], ["calm", "focused"])
            self.assertEqual(payload["correspondence_summary"]["target_descriptors"], ["softer-contrast"])
            self.assertEqual(payload["correspondence_summary"]["ambiguity_note_count"], 1)

    def test_mrwif_diff_reports_correspondence_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            left_path = tmp_dir / "left.yaml"
            right_path = tmp_dir / "right.yaml"
            left_path.write_text(
                "\n".join(
                    [
                        "correspondence_id: product-id-01",
                        "linked_artifacts:",
                        "  - realm: rwif",
                        "    artifact_id: concept.product",
                        "  - realm: arwif",
                        "    artifact_id: audio.product.v1",
                        "intent_mappings:",
                        "  - mapping_id: intent.core",
                        "    semantic_descriptors:",
                        "      - confident",
                        "    target_realm: arwif",
                        "    target_descriptors:",
                        "      - tighter-transient",
                        "interpretation_records:",
                        "  - record_id: interp.audio.v1",
                        "    artifact_id: audio.product.v1",
                        "    inferred_descriptors:",
                        "      - confident",
                        "revision_traces:",
                        "  - revision_id: rev.01",
                        "    requested_changes:",
                        "      - add urgency",
                        "    applied_changes:",
                        "      - shorter release",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            right_path.write_text(
                "\n".join(
                    [
                        "correspondence_id: product-id-01",
                        "title: Revised product identity",
                        "linked_artifacts:",
                        "  - realm: rwif",
                        "    artifact_id: concept.product",
                        "  - realm: arwif",
                        "    artifact_id: audio.product.v2",
                        "  - realm: vrwif",
                        "    artifact_id: visual.product.v1",
                        "intent_mappings:",
                        "  - mapping_id: intent.core",
                        "    semantic_descriptors:",
                        "      - confident",
                        "      - urgent",
                        "    target_realm: arwif",
                        "    target_descriptors:",
                        "      - tighter-transient",
                        "      - faster-rise",
                        "    confidence: 0.9",
                        "interpretation_records:",
                        "  - record_id: interp.audio.v2",
                        "    artifact_id: audio.product.v2",
                        "    inferred_descriptors:",
                        "      - confident",
                        "      - urgent",
                        "    ambiguity_notes:",
                        "      - edges toward aggressive",
                        "revision_traces:",
                        "  - revision_id: rev.02",
                        "    requested_changes:",
                        "      - add urgency",
                        "      - extend visual support",
                        "    applied_changes:",
                        "      - shorter release",
                        "      - brighter contrast",
                        "    affected_realms:",
                        "      - arwif",
                        "      - vrwif",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self._run_json(repo_root, "mrwif-diff", str(left_path), str(right_path), "--json")
            self.assertTrue(payload["left_valid"], payload)
            self.assertTrue(payload["right_valid"], payload)
            self.assertIn("title", payload["metadata_changes"])
            self.assertEqual(payload["correspondence_changes"]["linked_artifact_count_delta"], 1)
            self.assertEqual(payload["correspondence_changes"]["semantic_descriptors_count_delta"], 1)
            self.assertEqual(payload["correspondence_changes"]["target_descriptors_count_delta"], 1)
            self.assertEqual(payload["correspondence_changes"]["ambiguity_note_count_delta"], 1)
            self.assertEqual(payload["correspondence_changes"]["revision_trace_count_delta"], 0)
            self.assertTrue(payload["correspondence_changes"]["linked_artifact_realms_changed"])
            self.assertEqual(payload["added_linked_artifacts"], ["audio.product.v2", "visual.product.v1"])
            self.assertEqual(payload["removed_linked_artifacts"], ["audio.product.v1"])
            self.assertEqual(payload["added_interpretation_records"], ["interp.audio.v2"])
            self.assertEqual(payload["removed_interpretation_records"], ["interp.audio.v1"])
            self.assertEqual(payload["added_revision_traces"], ["rev.02"])
            self.assertEqual(payload["removed_revision_traces"], ["rev.01"])

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
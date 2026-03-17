from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DiffPatchIntegrationTest(unittest.TestCase):
    def test_diff_and_patch_track_source_changes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            docs_dir = tmp_dir / "docs"
            docs_dir.mkdir()
            source_path = docs_dir / "note.md"
            source_path.write_text("# Intro\n\nHello wave memory.\n", encoding="utf-8")

            config_path = tmp_dir / "rwif.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "project: diff-patch-demo",
                        "version: 0.1.0",
                        "sources:",
                        f"  - path: {docs_dir}",
                        "    include:",
                        '      - "**/*.md"',
                        "chunking:",
                        "  strategy: markdown_sections",
                        "  max_tokens: 64",
                        "  overlap_tokens: 8",
                        "embedding:",
                        "  provider: hashing",
                        "  model: rwif-hash-v1",
                        "  vector_length: 128",
                        "top_k_waves: 32",
                        "output:",
                        f"  path: {tmp_dir / 'base.rwif'}",
                    ]
                ),
                encoding="utf-8",
            )

            self._run(repo_root, "build", "--config", str(config_path), "--output", str(tmp_dir / "base.rwif"))

            source_path.write_text("# Intro\n\nHello wave memory.\n\n## Update\n\nA new section was added.\n", encoding="utf-8")
            self._run(repo_root, "build", "--config", str(config_path), "--output", str(tmp_dir / "next.rwif"))

            diff_payload = self._run_json(repo_root, "diff", str(tmp_dir / "base.rwif"), str(tmp_dir / "next.rwif"), "--json")
            self.assertIn("note.md", diff_payload["changed_sources"])
            self.assertEqual(diff_payload["change_summary"]["changed"], 1)

            patched_path = tmp_dir / "patched.rwif"
            patch_payload = self._run_json(
                repo_root,
                "patch",
                "--config",
                str(config_path),
                "--base",
                str(tmp_dir / "base.rwif"),
                "--output",
                str(patched_path),
                "--json",
            )
            self.assertEqual(patch_payload["status"], "patched")
            self.assertTrue(patched_path.exists())
            self.assertIn("note.md", patch_payload["changed_sources"])

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

    def _run_json(self, repo_root: Path, *args: str) -> dict[str, object]:
        return json.loads(self._run(repo_root, *args))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliInitTest(unittest.TestCase):
    def test_init_creates_config(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            output_path = Path(tmp_dir_str) / "rwif.yaml"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rwif_builder.cli",
                    "init",
                    "--output",
                    str(output_path),
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
                env={"PYTHONPATH": str(repo_root / "src")},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.exists())
            self.assertIn("project:", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_init_creates_config(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "rwif.yaml"

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

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert "project:" in output_path.read_text(encoding="utf-8")

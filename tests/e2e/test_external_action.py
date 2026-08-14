from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_external_action_path_installs_agentproof(tmp_path: Path):
    action_root = Path(__file__).resolve().parents[2]
    external_workspace = tmp_path / "external-repository"
    external_workspace.mkdir()
    (external_workspace / "README.md").write_text("external workspace\n")
    env = {**os.environ, "GITHUB_ACTION_PATH": str(action_root)}
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", str(action_root)], cwd=external_workspace, env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    help_result = subprocess.run([sys.executable, "-m", "agentproof", "explain", "AP001"], cwd=external_workspace, env=env, text=True, capture_output=True, check=False)
    assert help_result.returncode == 0
    assert "Test Deleted" in help_result.stdout

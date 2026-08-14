from __future__ import annotations

import subprocess
from pathlib import Path

from agentproof.engine.verifier import verify_core
from agentproof.policy.evaluator import preset


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def test_core_pipeline_proves_real_fix(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof Test"], cwd=repo, check=True)
    (repo / "app.py").write_text("def ready(value):\n    return value == 'ready'\n")
    (repo / "test_app.py").write_text("from app import ready\n\ndef test_pending_is_ready():\n    assert ready('pending') is True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "app.py").write_text("def ready(value):\n    return value in {'ready', 'pending'}\n")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fix"], cwd=repo, check=True)
    head = _git(repo, "rev-parse", "HEAD")
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", ["python3 -m pytest -q test_app.py::test_pending_is_ready"], ["Added regression coverage"], preset("strict"), timeout=60)
    assert receipt.verdict == "VERIFIED"
    assert receipt.proof_tests[0]["status"] == "PROVEN"
    assert receipt.receipt_sha256.startswith("sha256:")

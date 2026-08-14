from __future__ import annotations

import subprocess
from pathlib import Path

from agentproof.checks import audit_diff


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def test_adversarial_skip_and_filter_are_reported(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof"], cwd=repo, check=True)
    (repo / "tests.py").write_text("def test_login():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = git(repo, "rev-parse", "HEAD")
    (repo / "tests.py").write_text("import pytest\n\ndef test_login():\n    pytest.mark.skip\n    assert True\n")
    (repo / ".github").mkdir()
    (repo / ".github" / "workflow.yml").write_text("pytest --ignore=tests/integration\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "head"], cwd=repo, check=True)
    head = git(repo, "rev-parse", "HEAD")
    findings, _ = audit_diff(repo, base, head)
    ids = {finding.rule for finding in findings}
    assert "AP002" in ids or "skip-added" in ids
    assert "AP004" in ids or "test-ignore" in ids

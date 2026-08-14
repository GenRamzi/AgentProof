from pathlib import Path

from agentproof.checks import audit_diff
from agentproof.models import TestRun
from agentproof.verifier import compare_proof_test


def test_proof_test_requires_base_fail_and_pr_pass():
    base = TestRun("pytest -q tests/test_login.py", "/tmp/base", 1, 0.1, "failed")
    head = TestRun("pytest -q tests/test_login.py", "/tmp/head", 0, 0.1, "passed")
    result = compare_proof_test("pytest -q tests/test_login.py", base, head)
    assert result.status == "PROVEN"


def test_already_passing_test_is_inconclusive():
    base = TestRun("pytest -q", "/tmp/base", 0, 0.1, "passed")
    head = TestRun("pytest -q", "/tmp/head", 0, 0.1, "passed")
    assert compare_proof_test("pytest -q", base, head).status == "INCONCLUSIVE"


def test_audit_detects_added_skip_and_ci_change(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "tests.py").write_text("def test_login():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "tests.py").write_text("import pytest\n\ndef test_login():\n    pytest.mark.skip\n    assert True\n")
    (repo / ".github").mkdir()
    (repo / ".github" / "ci.yml").write_text("pytest --ignore=tests/integration\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "head"], cwd=repo, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    findings, evidence = audit_diff(repo, base, head)
    rules = {finding.rule for finding in findings}
    assert "skip-added" in rules
    assert "ci-changed" in rules
    assert evidence["changed_files"]

from __future__ import annotations

from pathlib import Path

from agentproof import __version__
from agentproof.engine.environment import fingerprint
from agentproof.engine.verifier import verify_core
from agentproof.policy.evaluator import preset
from agentproof.receipt.verify import verify_receipt_data


def test_invalid_receipt_fails_schema_and_digest():
    data = {
        "schema": "agentproof.receipt/v1",
        "subject": {"repository": "o/r", "base_sha": "b", "head_sha": "h"},
        "verdict": "VERIFIED",
        "claims": [],
        "proof_tests": [],
        "test_runs": [],
        "integrity_findings": [],
        "environment": {},
        "policy": {},
        "digest": "sha256:" + "0" * 64,
    }
    valid, _, actual = verify_receipt_data(data)
    assert not valid
    assert actual.startswith(("schema-invalid:", "sha256:"))


def test_local_environment_is_not_github_actions(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    environment = fingerprint(tmp_path, network_mode="deny", runner_type="local")
    assert environment["runner_type"] == "local"
    assert environment["agentproof_version"] == __version__


def test_enterprise_policy_requires_attestations(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof"], cwd=repo, check=True)
    (repo / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "head"], cwd=repo, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", [], [], preset("enterprise"), timeout=60)
    assert receipt.verdict == "BLOCKED"
    assert {finding.rule for finding in receipt.findings} >= {"AP501", "AP502"}

from __future__ import annotations

import subprocess
from pathlib import Path

from agentproof.adapters.discover import discover_setup_command
from agentproof.engine.verifier import verify_core
from agentproof.models import TestRun, VerificationReceipt
from agentproof.policy.evaluator import preset


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof Test"], cwd=repo, check=True)
    (repo / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "head"], cwd=repo, check=True)
    return repo, base, _git(repo, "rev-parse", "HEAD")


def test_setup_discovery_covers_lockfiles_and_ecosystems(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}', encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    assert discover_setup_command(tmp_path) == "npm ci"

    (tmp_path / "package-lock.json").unlink()
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9", encoding="utf-8")
    assert discover_setup_command(tmp_path) == "pnpm install --frozen-lockfile"

    (tmp_path / "pnpm-lock.yaml").unlink()
    (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    assert discover_setup_command(tmp_path) == "npm install && python -m pip install -r requirements-dev.txt"

    (tmp_path / "requirements-dev.txt").unlink()
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/demo\n\ngo 1.22\n", encoding="utf-8")
    assert discover_setup_command(tmp_path) == "npm install && cargo fetch && go mod download"


def test_legacy_boolean_policy_normalizes_to_modes():
    from agentproof.policy.evaluator import load_policy

    assert load_policy(name="default")["verification"]["proof_tests"] == "auto"
    assert load_policy(name="strict")["verification"]["proof_tests"] == "auto"


def test_setup_failure_is_inconclusive_and_recorded(tmp_path: Path):
    repo, base, head = _repo(tmp_path)
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", policy=preset("default"), setup_command="false", timeout=30)
    assert receipt.verdict == "INCONCLUSIVE"
    assert any(finding.rule == "AP204" for finding in receipt.findings)
    assert receipt.test_runs["head"].exit_code == 125
    assert receipt.setup_runs["base"].exit_code != 0
    claim = next(item for item in receipt.evidence["claims"] if item["type"] == "tests_pass")
    assert claim["status"] == "UNPROVEN"


def test_setup_runs_round_trip_losslessly(tmp_path: Path):
    repo, base, head = _repo(tmp_path)
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", policy=preset("default"), setup_command="true", timeout=30)
    restored = VerificationReceipt.from_dict(receipt.to_dict())
    assert restored.to_dict() == receipt.to_dict()
    assert isinstance(restored.setup_runs["base"], TestRun)
    assert restored.setup_runs["head"].exit_code == 0


def test_strict_auto_does_not_require_proof_for_readme_only_change(tmp_path: Path):
    repo, base, head = _repo(tmp_path)
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", policy=preset("strict"), setup_command="true", timeout=30)
    assert receipt.verdict == "VERIFIED"
    assert receipt.evidence["proof_tests_mode"] == "auto"
    assert receipt.evidence["proof_tests_required"] is False


def test_manual_proof_runs_setup_and_records_evidence(tmp_path: Path):
    repo, base, head = _repo(tmp_path)
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", ["python3 -m pytest -q"], policy=preset("default"), setup_command="true", timeout=30)
    assert "proof-base" in receipt.setup_runs
    assert "proof-head" in receipt.setup_runs
    assert receipt.setup_runs["proof-base"].exit_code == 0
    assert receipt.proof_tests


def test_manual_proof_setup_failure_is_unreproducible(tmp_path: Path):
    repo, base, head = _repo(tmp_path)
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", ["python3 -m pytest -q"], policy=preset("default"), setup_command="false", timeout=30)
    assert receipt.proof_tests[0]["status"] == "UNREPRODUCIBLE"
    assert any(finding.rule == "AP204" for finding in receipt.findings)


def test_transplanted_proof_runs_setup(tmp_path: Path):
    repo, base, _ = _repo(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "tests/test_new.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "new test"], cwd=repo, check=True)
    head = _git(repo, "rev-parse", "HEAD")
    receipt = verify_core(repo, base, head, "python3 -m pytest -q", policy=preset("default"), setup_command="true", timeout=30)
    assert any(name.startswith("transplant-") for name in receipt.setup_runs)
    assert receipt.proof_tests

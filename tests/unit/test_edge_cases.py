from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

import pytest

from agentproof.adapters.discover import (
    CommandDiscoveryError,
    discover_canonical_command,
    discover_test_commands,
)
from agentproof.engine.executor import execute
from agentproof.engine.worktrees import WorktreeManager
from agentproof.models import Finding
from agentproof.policy.evaluator import (
    action_for,
    evaluate_findings,
    load_policy,
    preset,
)
from agentproof.proof.tests import targeted_command
from agentproof.receipt.verify import validate_receipt_schema


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def test_discover_commands_for_multiple_ecosystems(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "jest", "test:unit": "jest unit"}}), encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example\n", encoding="utf-8")
    commands = discover_test_commands(tmp_path)
    assert commands == ["pytest -q", "npm test", "npm run test:unit", "cargo test", "go test ./..."]


def test_discover_ignores_malformed_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{broken", encoding="utf-8")
    assert discover_test_commands(tmp_path) == []


def test_discover_canonical_command_errors_are_actionable(tmp_path: Path) -> None:
    with pytest.raises(CommandDiscoveryError, match="No canonical"):
        discover_canonical_command(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts":{"test":"jest"}}', encoding="utf-8")
    with pytest.raises(CommandDiscoveryError, match="Ambiguous"):
        discover_canonical_command(tmp_path)
    assert discover_canonical_command(tmp_path, "custom test") == "custom test"


def test_policy_parser_and_evaluator_handle_invalid_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_policy(tmp_path / "missing.yml")
    invalid = tmp_path / "invalid.yml"
    invalid.write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(TypeError, match="mapping"):
        load_policy(invalid)
    with pytest.raises(ValueError):
        preset("unknown")
    policy = preset("strict")
    assert action_for(policy, "AP301") == "review"
    assert action_for(policy, "AP999") == "warning"
    findings = [Finding("AP001", "low", "blocked"), Finding("AP002", "low", "review")]
    evaluate_findings(findings, {"integrity": {"deleted_tests": "block", "new_skips": "review"}})
    assert findings[0].severity == "high"
    assert findings[1].severity == "medium"


def test_executor_counts_output_and_handles_timeout(tmp_path: Path) -> None:
    passed = execute("python -c \"print('1 passed')\"", tmp_path, "HEAD", timeout=5)
    assert passed.passed
    assert passed.test_counts == {"passed": 1}
    timed_out = execute("python -c \"import time; time.sleep(1)\"", tmp_path, "HEAD", timeout=0)
    assert timed_out.exit_code == 124
    assert "timed out" in timed_out.output_tail


def test_executor_handles_missing_command(tmp_path: Path) -> None:
    evidence = execute("definitely-not-a-real-agentproof-command", tmp_path, "HEAD", timeout=5)
    assert evidence.exit_code == 127
    assert "not found" in evidence.output_tail.lower()


def test_worktree_create_transplant_and_cleanup(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof"], cwd=repo, check=True)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_added.py").write_text("def test_added():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = git(repo, "rev-parse", "HEAD")
    (repo / "tests" / "test_added.py").write_text("def test_added():\n    assert 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "head"], cwd=repo, check=True)
    head = git(repo, "rev-parse", "HEAD")
    manager = WorktreeManager(repo)
    created = manager.create(base, "base")
    assert (created / "tests" / "test_added.py").is_file()
    transplanted = manager.create_transplant(base, head, "tests/test_added.py", "transplant")
    assert "assert 1" in (transplanted / "tests" / "test_added.py").read_text(encoding="utf-8")
    manager.cleanup()
    assert not (repo / ".agentproof-worktrees").exists()


def test_targeted_commands_quote_attacker_controlled_paths() -> None:
    paths = ["tests/test a.py", "tests/$TEST.py", "../../test.py", "tests/it's.py", "tests/é.py", "tests/test.py; echo pwned.py"]
    for path in paths:
        command = targeted_command("pytest -q", path)
        assert shlex.split(command)[2] == path
        assert command.startswith("pytest -q ")
    assert targeted_command("jest", "tests/$TEST.js").startswith("npx jest '")


def test_receipt_schema_reports_missing_schema_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENTPROOF_RECEIPT_SCHEMA", str(tmp_path / "missing.json"))
    valid, error = validate_receipt_schema({})
    assert not valid
    assert "not found" in error

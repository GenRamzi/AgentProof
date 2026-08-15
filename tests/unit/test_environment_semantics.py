from pathlib import Path

from agentproof.engine.environment import fingerprint
from agentproof.engine.evidence import RunEvidence
from agentproof.proof.tests import classify


def _run(environment: str, lock_hash: str, exit_code: int) -> RunEvidence:
    return RunEvidence(
        revision="BASE" if exit_code else "HEAD",
        command="pytest -q",
        cwd="/tmp",
        exit_code=exit_code,
        duration_seconds=0.1,
        stdout_hash="",
        stderr_hash="",
        output_tail="",
        environment_fingerprint=environment,
        dependency_lock_hash=lock_hash,
    )


def test_lockfile_change_is_not_ap205(tmp_path: Path):
    base = tmp_path / "base"
    head = tmp_path / "head"
    base.mkdir()
    head.mkdir()
    (base / "requirements.txt").write_text("pytest==8.0\n", encoding="utf-8")
    (head / "requirements.txt").write_text("pytest==8.1\n", encoding="utf-8")
    base_env = fingerprint(base)
    head_env = fingerprint(head)
    assert base_env["fingerprint"] == head_env["fingerprint"]
    assert base_env["dependency_lock_hash"] != head_env["dependency_lock_hash"]
    result = classify("pytest -q", _run(str(base_env["fingerprint"]), str(base_env["dependency_lock_hash"]), 1), _run(str(head_env["fingerprint"]), str(head_env["dependency_lock_hash"]), 0))
    assert result["status"] == "PROVEN"


def test_runtime_fingerprint_difference_is_ap205():
    result = classify("pytest -q", _run("sha256:base", "sha256:same", 1), _run("sha256:head", "sha256:same", 0))
    assert result["status"] == "ENVIRONMENT_MISMATCH"

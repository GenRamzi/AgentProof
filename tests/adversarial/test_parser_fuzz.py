from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import pytest

from agentproof.engine.worktrees import WorktreeManager
from agentproof.models import TestRun, VerificationReceipt
from agentproof.policy.evaluator import action_for, load_policy
from agentproof.receipt.verify import verify_receipt, verify_receipt_data


def test_receipts_round_trip_random_unicode_and_long_output() -> None:
    rng = random.Random(20260815)
    alphabet = "AgentProof-安全-Δ-🚫-\\n"
    for index in range(20):
        text = "".join(rng.choice(alphabet) for _ in range(2000))
        claims = [{"type": "correctness", "status": "PROVEN"}, {"type": "correctness", "status": "PROVEN"}]
        receipt = VerificationReceipt(
            schema_version="agentproof.receipt/v1",
            receipt_id=f"fuzz-{index}-{text[:8]}",
            created_at="now",
            verifier_version="0.2.0rc1",
            verdict="VERIFIED",
            base="a" * 40,
            head="b" * 40,
            claims=claims,  # type: ignore[arg-type]
            evidence={"claims": claims},
            test_runs={"base": TestRun("pytest -q", "/tmp", 1, 0.1, text)},
            subject={"repository": "example/repo", "base_sha": "a" * 40, "head_sha": "b" * 40},
        ).finalize()
        data = receipt.to_dict()
        assert VerificationReceipt.from_dict(data).to_dict() == data


def test_malformed_json_is_rejected_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    path.write_text('{"schema":', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        verify_receipt(path)


def test_invalid_digests_and_duplicate_claims_are_not_accepted() -> None:
    data = {
        "schema": "agentproof.receipt/v1",
        "subject": {"repository": "example/repo", "base_sha": "a", "head_sha": "b"},
        "verdict": "VERIFIED",
        "claims": [{"type": "x", "status": "PROVEN"}, {"type": "x", "status": "PROVEN"}],
        "proof_tests": [],
        "test_runs": [],
        "integrity_findings": [],
        "environment": {},
        "policy": {},
        "digest": "sha256:not-a-sha",
    }
    valid, _, reason = verify_receipt_data(data)
    assert not valid
    assert reason.startswith("schema-invalid:")


def test_unknown_policy_keys_and_invalid_actions_are_safe(tmp_path: Path) -> None:
    path = tmp_path / "agentproof.yml"
    path.write_text("version: 1\nfuture_key: [unicode, \"\u03bb\"]\nintegrity:\n  deleted_tests: explode\n", encoding="utf-8")
    policy = load_policy(path)
    assert policy["future_key"] == ["unicode", "λ"]
    assert action_for(policy, "AP001") == "warning"


def test_invalid_git_ref_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    manager = WorktreeManager(repo)
    with pytest.raises(subprocess.CalledProcessError):
        manager.create("not-a-valid-ref", "invalid")
    manager.cleanup()

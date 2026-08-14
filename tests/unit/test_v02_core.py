from __future__ import annotations

from pathlib import Path

from agentproof.checks.tests.assertions import detect_assertion_weakening
from agentproof.engine.evidence import RunEvidence
from agentproof.policy.evaluator import preset
from agentproof.proof.tests import classify
from agentproof.receipt.model import Receipt
from agentproof.receipt.verify import verify_receipt_data
from agentproof.rules import RULES


def _run(exit_code: int) -> RunEvidence:
    return RunEvidence("HEAD", "pytest -q", "/tmp", exit_code, 0.1, "sha256:a", "sha256:b", "", {}, "fp")


def test_rule_ids_are_stable():
    assert RULES["AP005"].title == "Assertion Weakened"
    assert RULES["AP401"].title == "API Contract Changed"


def test_proof_taxonomy():
    assert classify("x", _run(1), _run(0))["status"] == "PROVEN"
    assert classify("x", _run(0), _run(0))["status"] == "INCONCLUSIVE"
    assert classify("x", _run(1), _run(1))["status"] == "NOT_FIXED"
    assert classify("x", _run(0), _run(1))["status"] == "REGRESSION"


def test_policy_presets():
    assert preset("default")["integrity"]["new_skips"] == "warning"
    assert preset("strict")["integrity"]["new_skips"] == "block"
    assert preset("enterprise")["receipt"]["signature_required"] is True


def test_receipt_digest_verifies():
    receipt = Receipt(schema_version="agentproof.receipt/v1", receipt_id="AP-test", created_at="now", verifier_version="0.2.0.dev0", verdict="VERIFIED", base="b", head="h", claims=[{"type": "tests_pass", "status": "PROVEN"}], subject={"repository": "o/r", "base_sha": "b", "head_sha": "h"}).finalize()
    data = receipt.to_dict()
    valid, expected, actual = verify_receipt_data(data)
    assert valid
    assert expected == actual


def test_python_assertion_weakening(tmp_path: Path):
    base = tmp_path / "base"
    head = tmp_path / "head"
    base.mkdir()
    head.mkdir()
    (base / "test_api.py").write_text("def test_status():\n    assert response.status_code == 200\n")
    (head / "test_api.py").write_text("def test_status():\n    assert response.status_code < 500\n")
    findings = detect_assertion_weakening(base, head, ["test_api.py"])
    assert any(finding.rule == "AP005" for finding in findings)

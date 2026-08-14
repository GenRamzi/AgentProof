from __future__ import annotations

import builtins
from copy import deepcopy

import pytest

from agentproof.models import Finding, TestRun, VerificationReceipt
from agentproof.receipt.sign import sign_payload, verify_signature
from agentproof.receipt.verify import verify_receipt_data


def make_receipt() -> VerificationReceipt:
    claims = [{
        "type": "correctness",
        "status": "PROVEN",
        "evidence": ["proof-1"],
        "explanation": "The targeted proof test passed on HEAD only.",
    }]
    receipt = VerificationReceipt(
        schema_version="agentproof.receipt/v1",
        receipt_id="receipt-1",
        created_at="2026-08-15T00:00:00Z",
        verifier_version="0.2.0rc1",
        verdict="VERIFIED",
        base="a" * 40,
        head="b" * 40,
        subject={"repository": "example/repo", "base_sha": "a" * 40, "head_sha": "b" * 40},
        claims=claims,  # type: ignore[arg-type]
        evidence={"claims": claims},
        findings=[Finding("AP001", "high", "No deleted tests.")],
        test_runs={
            "base": TestRun("pytest -q", "/tmp/base", 1, 0.1, "failed"),
            "head": TestRun("pytest -q", "/tmp/head", 0, 0.1, "passed"),
        },
        environment={"runner_type": "local", "python": "3.11"},
        policy={"receipt": {"signature_required": False}},
        evidence_graph={"nodes": [], "edges": []},
    )
    return receipt.finalize()


def test_receipt_round_trip_is_lossless() -> None:
    receipt = make_receipt()
    data = receipt.to_dict()
    loaded = VerificationReceipt.from_dict(data)
    assert loaded.to_dict() == data


def test_receipt_tampering_changes_verification() -> None:
    data = make_receipt().to_dict()
    tampered = deepcopy(data)
    tampered["verdict"] = "BLOCKED"
    valid, _, _ = verify_receipt_data(tampered)
    assert not valid


def test_receipt_missing_required_field_fails_schema() -> None:
    data = make_receipt().to_dict()
    data.pop("subject")
    valid, _, actual = verify_receipt_data(data)
    assert not valid
    assert actual.startswith("schema-invalid:")


def test_receipt_wrong_schema_fails_schema_validation() -> None:
    data = make_receipt().to_dict()
    data["schema"] = "agentproof.receipt/v9"
    valid, _, actual = verify_receipt_data(data)
    assert not valid
    assert actual.startswith("schema-invalid:")


def test_receipt_wrong_digest_fails_digest_validation() -> None:
    data = make_receipt().to_dict()
    data["digest"] = "sha256:" + "0" * 64
    valid, expected, actual = verify_receipt_data(data)
    assert not valid
    assert expected == data["digest"]
    assert actual.startswith("sha256:")
    assert actual != expected


def _cryptography_or_skip():
    return pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")


def signed_data() -> tuple[dict[str, object], bytes]:
    _cryptography_or_skip()
    key = b"\x01" * 32
    receipt = make_receipt()
    receipt.signature = sign_payload(receipt.stable_unsigned_dict(), key)
    receipt.policy = {"receipt": {"signature_required": True}}
    receipt.signature = sign_payload(receipt.stable_unsigned_dict(), key)
    receipt.finalize()
    return receipt.to_dict(), key


def test_signature_required_rejects_missing_signature() -> None:
    data = make_receipt().to_dict()
    data["policy"] = {"receipt": {"signature_required": True}}
    valid, _, reason = verify_receipt_data(data)
    assert not valid
    assert reason == "signature-required"


def test_valid_ed25519_signature_verifies() -> None:
    data, _ = signed_data()
    valid, _, _ = verify_receipt_data(data)
    assert valid


def test_modified_signed_payload_is_rejected() -> None:
    data, _ = signed_data()
    data["verdict"] = "BLOCKED"
    valid, _, _ = verify_receipt_data(data)
    assert not valid


def test_modified_signature_is_rejected() -> None:
    data, _ = signed_data()
    signature = dict(data["signature"])  # type: ignore[arg-type]
    signature["signature"] = "0" + str(signature["signature"])[1:]
    data["signature"] = signature
    valid, _, reason = verify_receipt_data(data)
    assert not valid
    assert reason == "signature-invalid"


def test_wrong_public_key_is_rejected() -> None:
    ed25519 = _cryptography_or_skip()
    data, _ = signed_data()
    other_key = ed25519.Ed25519PrivateKey.generate()
    public = other_key.public_key().public_bytes_raw().hex()
    signature = dict(data["signature"])  # type: ignore[arg-type]
    signature["public_key"] = public
    data["signature"] = signature
    valid, _, reason = verify_receipt_data(data)
    assert not valid
    assert reason == "signature-invalid"


def test_malformed_private_key_is_rejected() -> None:
    _cryptography_or_skip()
    with pytest.raises(ValueError):
        sign_payload({}, b"bad")


def test_missing_cryptography_is_handled_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def blocked_import(name: str, *args: object, **kwargs: object):
        if name.startswith("cryptography"):
            raise ImportError("cryptography intentionally unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    with pytest.raises(RuntimeError, match="Install cryptography"):
        sign_payload({}, b"\x01" * 32)
    assert not verify_signature({}, {"public_key": "00", "signature": "00"})

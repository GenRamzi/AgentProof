from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    files: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    line: int | None = None
    category: str = "integrity"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def rule_id(self) -> str:
        return self.rule


@dataclass
class TestRun:
    command: str
    cwd: str
    exit_code: int
    duration_seconds: float
    output_tail: str
    stdout_hash: str = ""
    stderr_hash: str = ""
    test_counts: dict[str, int] = field(default_factory=dict)
    environment_fingerprint: str = ""
    commit_sha: str = ""
    dependency_lock_hash: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


@dataclass
class ProofTestResult:
    command: str
    base: TestRun
    head: TestRun
    status: str
    interpretation: str
    test_file: str = ""


@dataclass
class ClaimResult:
    type: str
    status: str
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class VerificationReceipt:
    schema_version: str
    receipt_id: str
    created_at: str
    verifier_version: str
    verdict: str
    base: str
    head: str
    claims: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    test_runs: dict[str, TestRun] = field(default_factory=dict)
    proof_tests: list[ProofTestResult] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    receipt_sha256: str = ""
    subject: dict[str, str] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)

    def stable_unsigned_dict(self) -> dict[str, Any]:
        runs = []
        for name, run in self.test_runs.items():
            item = asdict(run)
            item.setdefault("revision", name.upper())
            runs.append(item)
        return {
            "schema": "agentproof.receipt/v1",
            "receipt_id": self.receipt_id,
            "verifier_version": self.verifier_version,
            "subject": self.subject or {"base_sha": self.base, "head_sha": self.head},
            "verdict": self.verdict,
            "claims": self.evidence.get("claims", self.claims),
            "proof_tests": [asdict(item) if hasattr(item, "__dataclass_fields__") else item for item in self.proof_tests],
            "test_runs": runs,
            "integrity_findings": [asdict(item) for item in self.findings],
            "environment": self.environment,
            "policy": self.policy,
            "evidence_graph": self.evidence_graph,
        }

    def unsigned_dict(self) -> dict[str, Any]:
        return self.stable_unsigned_dict()

    def to_dict(self) -> dict[str, Any]:
        payload = self.stable_unsigned_dict()
        payload["digest"] = self.receipt_sha256
        payload["receipt_sha256"] = self.receipt_sha256
        return payload


# Prevent pytest from treating this data model as a test class when imported.
TestRun.__test__ = False

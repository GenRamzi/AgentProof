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


@dataclass
class TestRun:
    command: str
    cwd: str
    exit_code: int
    duration_seconds: float
    output_tail: str

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


@dataclass
class VerificationReceipt:
    schema_version: str
    receipt_id: str
    created_at: str
    verifier_version: str
    verdict: str
    base: str
    head: str
    claims: list[str]
    evidence: dict[str, Any]
    findings: list[Finding]
    test_runs: dict[str, TestRun]
    proof_tests: list[ProofTestResult]
    environment: dict[str, str]
    receipt_sha256: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("receipt_sha256", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Prevent pytest from treating this data model as a test class when imported.
TestRun.__test__ = False

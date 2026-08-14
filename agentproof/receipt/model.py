from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .canonical import digest


@dataclass
class Claim:
    type: str
    status: str
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class Receipt:
    schema: str
    subject: dict[str, str]
    verdict: str
    claims: list[Claim] = field(default_factory=list)
    proof_tests: list[dict[str, Any]] = field(default_factory=list)
    test_runs: list[dict[str, Any]] = field(default_factory=list)
    integrity_findings: list[dict[str, Any]] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)
    digest: str = ""
    signature: dict[str, Any] | None = None

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("digest", None)
        payload.pop("signature", None)
        payload["claims"] = [asdict(claim) if isinstance(claim, Claim) else claim for claim in self.claims]
        return payload

    def finalize(self) -> "Receipt":
        self.digest = digest(self.unsigned_payload())
        return self

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["claims"] = [asdict(claim) if isinstance(claim, Claim) else claim for claim in self.claims]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Receipt":
        claims = [Claim(**claim) if isinstance(claim, dict) else claim for claim in data.pop("claims", [])]
        return cls(claims=claims, **data)

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceNode:
    node_id: str
    kind: str
    value: Any
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunEvidence:
    revision: str
    command: str
    cwd: str
    exit_code: int
    duration_seconds: float
    stdout_hash: str
    stderr_hash: str
    output_tail: str
    test_counts: dict[str, int] = field(default_factory=dict)
    environment_fingerprint: str = ""
    commit_sha: str = ""
    dependency_lock_hash: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceGraph:
    nodes: list[EvidenceNode] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)

    def add(self, node: EvidenceNode) -> None:
        self.nodes.append(node)

    def link(self, source: str, target: str, relation: str) -> None:
        self.edges.append({"source": source, "target": target, "relation": relation})

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [asdict(node) for node in self.nodes], "edges": self.edges}

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MutationCandidate:
    file: str
    line: int
    description: str
    command: str


def changed_line_candidates(repo: Path, changed_files: list[str], command: str) -> list[MutationCandidate]:
    candidates: list[MutationCandidate] = []
    for relative in changed_files:
        path = repo / relative
        if not path.is_file() or path.suffix not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(token in line for token in ("if ", "assert ", "return ", "==", "!=", "===", "!==")):
                candidates.append(MutationCandidate(relative, index, "candidate changed-line mutation", command))
    return candidates


def explain_mutation_result(killed: bool) -> str:
    return "Mutation was detected by the proof test." if killed else "Your test did not catch the targeted mutation."

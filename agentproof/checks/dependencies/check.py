from __future__ import annotations

import re

from ...models import Finding

LOCKFILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "Cargo.lock", "go.sum"}


def detect_dependency_integrity(changed_files: list[str], diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path in changed_files:
        if path in LOCKFILES:
            findings.append(Finding("AP302", "medium", "A dependency lockfile changed and requires review.", files=[path]))
    for path, chunks in diff.items():
        if path not in {"package.json", "pyproject.toml", "Cargo.toml", "go.mod"}:
            continue
        added = [text.strip() for _, text in chunks["added"]]
        dependency_lines = [text for text in added if re.search(r"(?:dependencies|devDependencies|requires|crate|require\s+\w+|\"[A-Za-z0-9_.@/-]+\"\s*:)", text, re.IGNORECASE)]
        if (path == "package.json" and len(dependency_lines) >= 2) or len(dependency_lines) >= 3:
            findings.append(Finding("AP301", "medium", "Dependency graph expansion may have been introduced.", files=[path], evidence=dependency_lines[:10]))
    return findings

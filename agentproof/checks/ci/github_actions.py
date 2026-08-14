from __future__ import annotations

import re

from ...models import Finding


def detect_ci_integrity(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, chunks in diff.items():
        if not (".github/" in path or path.lower() in {"tox.ini", "pytest.ini", "pyproject.toml", "package.json", "makefile", "cargo.toml", "go.mod"}):
            continue
        added = [text.strip() for _, text in chunks["added"]]
        removed = [text.strip() for _, text in chunks["removed"]]
        if any(re.search(r"^\s*(test|tests|build|lint|integration)[-_ ]?\w*\s*:\s*$", text, re.IGNORECASE) for text in removed):
            findings.append(Finding("AP101", "high", "A CI job appears to have been removed.", files=[path], evidence=removed[:10]))
        if any(re.search(r"paths-ignore|branches-ignore|pull_request_target|on:\s*$", text, re.IGNORECASE) for text in added):
            findings.append(Finding("AP102", "high", "A CI trigger or path filter became narrower or more privileged.", files=[path], evidence=added[:10]))
        config_manipulation = any(re.search(r"(?:pytest|jest|vitest|npm\s+(?:run\s+)?test|cargo\s+test|go\s+test|timeout\s*[=:]|retries\s*[=:])", text, re.IGNORECASE) for text in added + removed)
        if config_manipulation and added and removed:
            findings.append(Finding("AP104", "medium", "CI or test configuration changed and requires independent review.", files=[path], evidence=[f"removed: {value}" for value in removed[:3]] + [f"added: {value}" for value in added[:3]]))
    return findings

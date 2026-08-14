from __future__ import annotations

import re

from ...models import Finding


def detect_mock_weakening(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, chunks in diff.items():
        if not any(token in path.lower() for token in ("test", "spec")):
            continue
        removed = [text.strip() for _, text in chunks["removed"]]
        added = [text.strip() for _, text in chunks["added"]]
        has_integration = any(re.search(r"integration_db|requests\.|httpx\.|database|client\.query", text, re.IGNORECASE) for text in removed)
        has_mock = any(re.search(r"(?:unittest\.mock|pytest\.mock|Mock\(|mock\()", text, re.IGNORECASE) for text in added)
        if has_integration and has_mock:
            findings.append(Finding("AP008", "medium", "Integration behavior appears to have been replaced by a mock.", files=[path], evidence=[f"removed: {item}" for item in removed if item][:3] + [f"added: {item}" for item in added if item][:3]))
    return findings

from __future__ import annotations

import re

from ...models import Finding

FOCUS_RE = re.compile(r"\.(?:only|focus)\s*\(|\b(?:fit|fdescribe|xonly|xit|xdescribe)\s*\(", re.IGNORECASE)


def detect_focused_tests(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, chunks in diff.items():
        if not any(token in path.lower() for token in ("test", "spec")):
            continue
        evidence = [f"{path}:{line}: {text.strip()}" for line, text in chunks["added"] if FOCUS_RE.search(text)]
        if evidence:
            findings.append(Finding("AP003", "high", "A focused-test marker was introduced; other tests may be excluded.", files=[path], evidence=evidence[:10]))
    return findings

from __future__ import annotations

import re

from ...models import Finding


SKIP_RE = re.compile(r"(?:pytest\.mark\.(?:skip|skipif|xfail)|unittest\.(?:skip|skipIf|expectedFailure)|\b(?:skip|xfail|xit|xdescribe)\b)", re.IGNORECASE)


def detect_added_skips(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, chunks in diff.items():
        if not any(token in path.lower() for token in ("test", "spec")):
            continue
        evidence = [f"{path}:{line}: {text.strip()}" for line, text in chunks["added"] if SKIP_RE.search(text)]
        if evidence:
            findings.append(Finding("AP002", "high", "A test skip or expected-failure marker was introduced.", files=[path], evidence=evidence[:10]))
    return findings

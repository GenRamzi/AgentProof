from __future__ import annotations

import re

from ...models import Finding


def detect_coverage_and_snapshots(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    coverage_re = re.compile(r"(?:no\s*cover|coverage\s+omit|(?:^|\s)(?:omit|exclude)\s*=|--cov-fail-under\s*=\s*0|coverageThreshold\s*:\s*\{\s*\})", re.IGNORECASE)
    snapshot_re = re.compile(r"(?:__snapshots__|--update-snapshots|jest\s+-u|vitest\s+-u)", re.IGNORECASE)
    for path, chunks in diff.items():
        added = [(line, text.strip()) for line, text in chunks["added"]]
        coverage = [f"{path}:{line}: {text}" for line, text in added if coverage_re.search(text)]
        snapshots = [f"{path}:{line}: {text}" for line, text in added if snapshot_re.search(text)]
        if coverage:
            findings.append(Finding("AP006", "medium", "A coverage exclusion or threshold weakening was detected.", files=[path], evidence=coverage[:10]))
        if snapshots:
            findings.append(Finding("AP007", "medium", "Snapshot update behavior was changed.", files=[path], evidence=snapshots[:10]))
    return findings

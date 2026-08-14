from __future__ import annotations

import re

from ...models import Finding


def detect_deleted_tests(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, chunks in diff.items():
        if not any(token in path.lower() for token in ("test", "spec")):
            continue
        evidence = [f"{path}: {text.strip()}" for _, text in chunks["removed"] if re.search(r"(?:def\s+test_|(?:it|test|describe)\s*\(|@Test\b)", text)]
        if evidence:
            findings.append(Finding("AP001", "high", "Test code appears to have been deleted in the pull request.", files=[path], evidence=evidence[:10]))
    return findings


def detect_discovery_reduction(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    patterns = re.compile(r"(?:--ignore(?:=|\s)|testpaths\s*=|norecursedirs\s*=|paths-ignore|exclude:|ignorePatterns|testMatch|pytest\s+tests/\S+)", re.IGNORECASE)
    for path, chunks in diff.items():
        if not (path.endswith((".yml", ".yaml", ".ini", ".toml", ".cfg", ".json", "Makefile")) or ".github/" in path):
            continue
        evidence = [f"{path}:{line}: {text.strip()}" for line, text in chunks["added"] if patterns.search(text)]
        if evidence:
            findings.append(Finding("AP004", "high", "Test discovery or filtering configuration changed and may reduce the suite scope.", files=[path], evidence=evidence[:10]))
    return findings


def detect_test_command_reduction(diff: dict[str, dict[str, list[tuple[int, str]]]]) -> list[Finding]:
    findings: list[Finding] = []
    command_re = re.compile(r"(?:pytest|jest|vitest|npm\s+(?:run\s+)?test|cargo\s+test|go\s+test)", re.IGNORECASE)
    for path, chunks in diff.items():
        if not (".github/" in path or path.lower() in {"makefile", "package.json", "pyproject.toml", "tox.ini", "pytest.ini"}):
            continue
        removed = [text.strip() for _, text in chunks["removed"] if command_re.search(text)]
        added = [text.strip() for _, text in chunks["added"] if command_re.search(text)]
        if removed and added and len(" ".join(added)) < len(" ".join(removed)):
            findings.append(Finding("AP103", "high", "The configured test command appears to cover a smaller scope.", files=[path], evidence=[f"Previously: {' | '.join(removed[:3])}", f"Now: {' | '.join(added[:3])}"]))
    return findings

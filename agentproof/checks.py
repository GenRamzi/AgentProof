from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .models import Finding


TEST_FILE_RE = re.compile(
    r"(^|/)(tests?|spec|__tests__)(/|$)|(^|/)(test[^/]*|[^/]*_test)\.(py|js|jsx|ts|tsx|go|rb|java)$|(_test\.|\.test\.|\.spec\.)",
    re.IGNORECASE,
)

SUSPICIOUS_PATTERNS: list[tuple[str, str, str]] = [
    ("skip-added", r"\b(skip|xit|xdescribe|pytest\.mark\.skip|unittest\.skip)\b", "A test skip marker was added."),
    ("focused-test", r"\.(only|focus)\s*\(", "A focused-test marker was added; other tests may be excluded."),
    ("assertion-weakened", r"^[+-].*(assert\s+True|assert\s+1\s*==\s*1|assert\s+True\s*$)", "An assertion may have been weakened."),
    ("coverage-exclusion", r"#\s*(noqa|pragma:\s*no cover)|coverage\s+omit|--cov-fail-under\s*=\s*0", "A coverage exclusion or threshold weakening was detected."),
    ("test-ignore", r"(--ignore|testpaths\s*=|norecursedirs\s*=|filterwarnings\s*=|ignore::)", "Test discovery or filtering configuration changed."),
    ("timeout-increase", r"timeout\s*[=:]\s*(\d{3,}|[6-9]\d|\d{3,})", "A potentially excessive test timeout was added or increased."),
    ("snapshot-regenerated", r"snapshot|__snapshots__|-u\b|--update-snapshots", "Snapshot update behavior was changed."),
]

CI_FILES = re.compile(r"(^|/)(\.github/|\.gitlab-ci|jenkinsfile|tox\.ini|pytest\.ini|noxfile|pyproject\.toml|package\.json)", re.IGNORECASE)


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", "color.ui=false", *args], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    output = git_output(repo, "diff", "--name-only", f"{base}..{head}")
    return [line.strip() for line in output.splitlines() if line.strip()]


def diff_text(repo: Path, base: str, head: str) -> str:
    return git_output(repo, "diff", "--unified=0", f"{base}..{head}", "--")


def audit_diff(repo: Path, base: str, head: str) -> tuple[list[Finding], dict[str, object]]:
    files = changed_files(repo, base, head)
    diff = diff_text(repo, base, head)
    findings: list[Finding] = []
    added_lines = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed_lines = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]

    test_files = [path for path in files if TEST_FILE_RE.search(path)]
    ci_files = [path for path in files if CI_FILES.search(path)]

    for rule, pattern, message in SUSPICIOUS_PATTERNS:
        matched = [line.strip() for line in added_lines if re.search(pattern, line, re.IGNORECASE)]
        if matched:
            severity = "high" if rule in {"skip-added", "focused-test", "test-ignore", "assertion-weakened"} else "medium"
            findings.append(Finding(rule, severity, message, files=test_files + ci_files, evidence=matched[:5]))

    deleted_tests = [line for line in removed_lines if re.search(r"def\s+test_|it\s*\(", line)]
    if deleted_tests:
        findings.append(Finding("test-deleted", "high", "Test code appears to have been deleted in the pull request.", files=test_files, evidence=deleted_tests[:5]))

    if ci_files:
        findings.append(Finding("ci-changed", "medium", "CI or test configuration changed and requires independent review.", files=ci_files))

    evidence = {
        "changed_files": files,
        "changed_test_files": test_files,
        "changed_ci_files": ci_files,
        "added_lines_scanned": len(added_lines),
        "removed_lines_scanned": len(removed_lines),
    }
    return findings, evidence

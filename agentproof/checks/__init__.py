from __future__ import annotations

from pathlib import Path

from .ci.github_actions import detect_ci_integrity
from .common import changed_files, diff_by_file
from .dependencies.check import detect_dependency_integrity
from .tests.discovery import (
    detect_deleted_tests,
    detect_discovery_reduction,
    detect_test_command_reduction,
)
from .tests.focus import detect_focused_tests
from .tests.mock import detect_mock_weakening
from .tests.skips import detect_added_skips
from .tests.snapshots import detect_coverage_and_snapshots


def audit_diff(repo: Path, base: str, head: str):
    files = changed_files(repo, base, head)
    diff = diff_by_file(repo, base, head)
    findings = []
    for detector in (detect_added_skips, detect_focused_tests, detect_mock_weakening, detect_deleted_tests, detect_discovery_reduction, detect_test_command_reduction, detect_coverage_and_snapshots, detect_ci_integrity):
        findings.extend(detector(diff))
    findings.extend(detect_dependency_integrity(files, diff))
    evidence = {
        "changed_files": files,
        "changed_test_files": [path for path in files if "test" in path.lower() or "spec" in path.lower()],
        "changed_ci_files": [path for path in files if ".github/" in path or path.lower() in {"pyproject.toml", "pytest.ini", "tox.ini", "package.json", "makefile"}],
        "added_lines_scanned": sum(len(chunks["added"]) for chunks in diff.values()),
        "removed_lines_scanned": sum(len(chunks["removed"]) for chunks in diff.values()),
    }
    return findings, evidence


__all__ = ["audit_diff"]

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from ..engine.evidence import RunEvidence
from ..engine.executor import execute
from ..engine.worktrees import WorktreeManager
from ..models import Finding


def classify(command: str, base: RunEvidence, head: RunEvidence) -> dict[str, object]:
    if not base.passed and head.passed:
        return {"command": command, "status": "PROVEN", "base": asdict(base), "head": asdict(head), "interpretation": "The proof test failed on BASE and passed on HEAD."}
    if base.passed and head.passed:
        return {"command": command, "status": "INCONCLUSIVE", "base": asdict(base), "head": asdict(head), "interpretation": "The proof test passed on both revisions and does not demonstrate a fix."}
    if not base.passed and not head.passed:
        return {"command": command, "status": "NOT_FIXED", "base": asdict(base), "head": asdict(head), "interpretation": "The proof test failed on both revisions."}
    return {"command": command, "status": "REGRESSION", "base": asdict(base), "head": asdict(head), "interpretation": "The proof test passed on BASE but failed on HEAD."}


def findings_for_proof(result: dict[str, object]) -> list[Finding]:
    status = result["status"]
    if status == "INCONCLUSIVE":
        return [Finding("AP201", "medium", "The proof test passes on both base and PR revisions.", evidence=[str(result["command"])])]
    if status in {"NOT_FIXED", "UNREPRODUCIBLE"}:
        return [Finding("AP202", "high", "The proof test does not pass on the PR revision.", evidence=[str(result["command"])])]
    if status == "REGRESSION":
        return [Finding("AP203", "high", "The proof test passed on base and failed on the PR revision.", evidence=[str(result["command"])])]
    return []


def discover_new_tests(changed_files: list[str]) -> list[str]:
    return [path for path in changed_files if re.search(r"(^|/)(tests?|spec|__tests__)/.*(?:test|spec)[^/]*\.(py|js|jsx|ts|tsx)$", path, re.IGNORECASE)]


def run_proof_tests(repo: Path, base: str, head: str, commands: list[str], timeout: int, fingerprint: str) -> tuple[list[dict[str, object]], list[Finding]]:
    results: list[dict[str, object]] = []
    findings: list[Finding] = []
    with WorktreeManager(repo) as worktrees:
        base_path = worktrees.create(base, "base")
        head_path = worktrees.create(head, "head")
        for command in commands:
            base_run = execute(command, base_path, "BASE", base, fingerprint, timeout)
            head_run = execute(command, head_path, "HEAD", head, fingerprint, timeout)
            result = classify(command, base_run, head_run)
            results.append(result)
            findings.extend(findings_for_proof(result))
    return results, findings


def run_transplanted_proofs(repo: Path, base: str, head: str, tests: list[str], test_command: str, timeout: int, fingerprint: str) -> tuple[list[dict[str, object]], list[Finding]]:
    results: list[dict[str, object]] = []
    findings: list[Finding] = []
    for index, relative in enumerate(tests):
        with WorktreeManager(repo) as worktrees:
            base_path = worktrees.create_transplant(base, head, relative, f"transplant-{index}")
            head_path = worktrees.create(head, f"head-{index}")
            base_run = execute(test_command, base_path, "BASE_TRANSPLANTED", base, fingerprint, timeout)
            head_run = execute(test_command, head_path, "HEAD", head, fingerprint, timeout)
            result = classify(f"transplanted:{relative}:{test_command}", base_run, head_run)
            result["test_file"] = relative
            results.append(result)
            findings.extend(findings_for_proof(result))
    return results, findings

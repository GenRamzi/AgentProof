from __future__ import annotations

import re
import shlex
from dataclasses import asdict
from pathlib import Path

from ..engine.evidence import RunEvidence
from ..engine.executor import execute
from ..engine.worktrees import WorktreeManager
from ..models import Finding


def _environment_mismatch(base: RunEvidence, head: RunEvidence) -> bool:
    fingerprints_differ = bool(base.environment_fingerprint and head.environment_fingerprint and base.environment_fingerprint != head.environment_fingerprint)
    lockfiles_differ = bool(base.dependency_lock_hash and head.dependency_lock_hash and base.dependency_lock_hash != head.dependency_lock_hash)
    return fingerprints_differ or lockfiles_differ


def _unreproducible(run: RunEvidence) -> bool:
    output = run.output_tail.lower()
    markers = (
        "agentproof: command timed out",
        "agentproof: unable to execute command",
        "command not found",
        "no module named",
        "modulenotfounderror",
        "importerror",
        "dependency resolution failed",
    )
    return run.exit_code in {124, 127} or any(marker in output for marker in markers)


def classify(command: str, base: RunEvidence, head: RunEvidence) -> dict[str, object]:
    if _environment_mismatch(base, head):
        status = "ENVIRONMENT_MISMATCH"
        interpretation = "BASE and HEAD were evaluated under materially different environments."
    elif _unreproducible(base) or _unreproducible(head):
        status = "UNREPRODUCIBLE"
        interpretation = "The proof test could not be executed reproducibly."
    elif not base.passed and head.passed:
        status = "PROVEN"
        interpretation = "The proof test failed on BASE and passed on HEAD."
    elif base.passed and head.passed:
        status = "INCONCLUSIVE"
        interpretation = "The proof test passed on both revisions and does not demonstrate a fix."
    elif not base.passed and not head.passed:
        status = "NOT_FIXED"
        interpretation = "The proof test failed on both revisions."
    else:
        status = "REGRESSION"
        interpretation = "The proof test passed on BASE but failed on HEAD."
    return {"command": command, "status": status, "base": asdict(base), "head": asdict(head), "interpretation": interpretation}


def findings_for_proof(result: dict[str, object]) -> list[Finding]:
    status = result["status"]
    if status == "INCONCLUSIVE":
        return [Finding("AP201", "medium", "The proof test passes on both base and PR revisions.", evidence=[str(result["command"])])]
    if status == "NOT_FIXED":
        return [Finding("AP202", "high", "The proof test does not pass on the PR revision.", evidence=[str(result["command"])])]
    if status == "UNREPRODUCIBLE":
        return [Finding("AP204", "high", "The proof test could not be executed reproducibly.", evidence=[str(result["command"])])]
    if status == "ENVIRONMENT_MISMATCH":
        return [Finding("AP205", "medium", "BASE and HEAD used materially different environments.", evidence=[str(result["command"])])]
    if status == "REGRESSION":
        return [Finding("AP203", "high", "The proof test passed on base and failed on the PR revision.", evidence=[str(result["command"])])]
    return []


def discover_new_tests(changed_files: list[str]) -> list[str]:
    return [path for path in changed_files if re.search(r"(^|/)(tests?|spec|__tests__)/.*(?:test|spec)[^/]*\.(py|js|jsx|ts|tsx)$", path, re.IGNORECASE)]


def targeted_command(test_command: str, test_file: str) -> str:
    lowered = test_command.lower()
    quoted_file = shlex.quote(test_file)
    if "pytest" in lowered or test_file.endswith(".py"):
        return f"pytest -q {quoted_file}"
    if "vitest" in lowered or test_file.endswith((".ts", ".tsx")):
        return f"npx vitest run {quoted_file}"
    if "jest" in lowered or test_file.endswith((".js", ".jsx")):
        return f"npx jest {quoted_file} --runInBand"
    return test_command


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
            targeted = targeted_command(test_command, relative)
            base_run = execute(targeted, base_path, "BASE_TRANSPLANTED", base, fingerprint, timeout)
            head_run = execute(targeted, head_path, "HEAD", head, fingerprint, timeout)
            result = classify(f"transplanted:{relative}:{targeted}", base_run, head_run)
            result["targeted_command"] = targeted
            result["test_file"] = relative
            results.append(result)
            findings.extend(findings_for_proof(result))
    return results, findings

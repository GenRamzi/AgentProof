from __future__ import annotations

import re
import shlex
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..adapters.discover import discover_setup_command
from ..engine.evidence import RunEvidence
from ..engine.executor import execute
from ..engine.worktrees import WorktreeManager
from ..models import Finding


def _environment_mismatch(base: RunEvidence, head: RunEvidence) -> bool:
    fingerprints_differ = bool(base.environment_fingerprint and head.environment_fingerprint and base.environment_fingerprint != head.environment_fingerprint)
    return fingerprints_differ


def _unreproducible(run: RunEvidence) -> bool:
    output = run.output_tail.lower()
    markers = (
        "agentproof: command timed out",
        "agentproof: unable to execute command",
        "agentproof: setup failed",
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


def _environment_values(environment: dict[str, Any]) -> tuple[str, str]:
    return str(environment.get("fingerprint", "")), str(environment.get("dependency_lock_hash", ""))


def _failed_setup_run(setup: RunEvidence, command: str, revision: str, commit_sha: str) -> RunEvidence:
    return RunEvidence(
        revision=revision,
        command=command,
        cwd=setup.cwd,
        exit_code=127,
        duration_seconds=setup.duration_seconds,
        stdout_hash=setup.stdout_hash,
        stderr_hash=setup.stderr_hash,
        output_tail=f"AgentProof: setup failed\n{setup.output_tail}",
        environment_fingerprint=setup.environment_fingerprint,
        commit_sha=commit_sha,
        dependency_lock_hash=setup.dependency_lock_hash,
    )


def _run_setup(path: Path, revision: str, commit_sha: str, configured: str | None, timeout: int, environment: dict[str, Any]) -> RunEvidence | None:
    command = discover_setup_command(path, configured)
    if command is None:
        return None
    fingerprint, lock_hash = _environment_values(environment)
    return execute(command, path, revision, commit_sha, fingerprint, timeout, lock_hash)


def run_proof_tests(
    repo: Path,
    base: str,
    head: str,
    commands: list[str],
    timeout: int,
    base_environment: dict[str, Any],
    head_environment: dict[str, Any],
    setup_command: str | None = None,
) -> tuple[list[dict[str, object]], list[Finding], dict[str, RunEvidence]]:
    results: list[dict[str, object]] = []
    findings: list[Finding] = []
    setup_runs: dict[str, RunEvidence] = {}
    base_fingerprint, base_lock_hash = _environment_values(base_environment)
    head_fingerprint, head_lock_hash = _environment_values(head_environment)
    with WorktreeManager(repo) as worktrees:
        base_path = worktrees.create(base, "base-proof")
        head_path = worktrees.create(head, "head-proof")
        base_setup = _run_setup(base_path, "BASE_PROOF_SETUP", base, setup_command, timeout, base_environment)
        head_setup = _run_setup(head_path, "HEAD_PROOF_SETUP", head, setup_command, timeout, head_environment)
        if base_setup:
            setup_runs["proof-base"] = base_setup
        if head_setup:
            setup_runs["proof-head"] = head_setup
        for command in commands:
            base_run = execute(command, base_path, "BASE_PROOF", base, base_fingerprint, timeout, base_lock_hash) if not base_setup or base_setup.passed else _failed_setup_run(base_setup, command, "BASE_PROOF", base)
            head_run = execute(command, head_path, "HEAD_PROOF", head, head_fingerprint, timeout, head_lock_hash) if not head_setup or head_setup.passed else _failed_setup_run(head_setup, command, "HEAD_PROOF", head)
            result = classify(command, base_run, head_run)
            results.append(result)
            findings.extend(findings_for_proof(result))
    return results, findings, setup_runs


def run_transplanted_proofs(
    repo: Path,
    base: str,
    head: str,
    tests: list[str],
    test_command: str,
    timeout: int,
    base_environment: dict[str, Any],
    head_environment: dict[str, Any],
    setup_command: str | None = None,
) -> tuple[list[dict[str, object]], list[Finding], dict[str, RunEvidence]]:
    results: list[dict[str, object]] = []
    findings: list[Finding] = []
    setup_runs: dict[str, RunEvidence] = {}
    base_fingerprint, base_lock_hash = _environment_values(base_environment)
    head_fingerprint, head_lock_hash = _environment_values(head_environment)
    for index, relative in enumerate(tests):
        with WorktreeManager(repo) as worktrees:
            base_path = worktrees.create_transplant(base, head, relative, f"transplant-{index}")
            head_path = worktrees.create(head, f"head-{index}")
            targeted = targeted_command(test_command, relative)
            base_setup = _run_setup(base_path, "BASE_TRANSPLANTED_SETUP", base, setup_command, timeout, base_environment)
            head_setup = _run_setup(head_path, "HEAD_TRANSPLANTED_SETUP", head, setup_command, timeout, head_environment)
            if base_setup:
                setup_runs[f"transplant-{index}-base"] = base_setup
            if head_setup:
                setup_runs[f"transplant-{index}-head"] = head_setup
            base_run = execute(targeted, base_path, "BASE_TRANSPLANTED", base, base_fingerprint, timeout, base_lock_hash) if not base_setup or base_setup.passed else _failed_setup_run(base_setup, targeted, "BASE_TRANSPLANTED", base)
            head_run = execute(targeted, head_path, "HEAD_TRANSPLANTED", head, head_fingerprint, timeout, head_lock_hash) if not head_setup or head_setup.passed else _failed_setup_run(head_setup, targeted, "HEAD_TRANSPLANTED", head)
            result = classify(f"transplanted:{relative}:{targeted}", base_run, head_run)
            result["targeted_command"] = targeted
            result["test_file"] = relative
            results.append(result)
            findings.extend(findings_for_proof(result))
    return results, findings, setup_runs

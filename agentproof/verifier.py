from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .checks import audit_diff
from .models import ProofTestResult, TestRun, VerificationReceipt
from .runner import run_command

VERSION = "0.1.0"


def checkout(repo: Path, ref: str, worktree: Path) -> None:
    if worktree.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo, check=False, capture_output=True)
    subprocess.run(["git", "worktree", "add", "--detach", str(worktree), ref], cwd=repo, check=True, text=True, capture_output=True)


def remove_worktree(repo: Path, worktree: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo, check=False, capture_output=True)


def compare_proof_test(command: str, base_run: TestRun, head_run: TestRun) -> ProofTestResult:
    if not base_run.passed and head_run.passed:
        status = "PROVEN"
        interpretation = "The proof test failed on the base revision and passed on the PR revision."
    elif base_run.passed and head_run.passed:
        status = "INCONCLUSIVE"
        interpretation = "The proof test passed on both revisions; it does not demonstrate that the PR fixed the defect."
    elif not base_run.passed and not head_run.passed:
        status = "NOT_FIXED"
        interpretation = "The proof test failed on both revisions; the claimed behavior is not independently demonstrated."
    else:
        status = "REGRESSION"
        interpretation = "The proof test passed on the base revision but failed on the PR revision."
    return ProofTestResult(command, base_run, head_run, status, interpretation)


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": os.environ.get("GITHUB_SHA", "unknown"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
        "network_policy": "caller-controlled; use a restricted runner for stronger isolation",
    }


def _receipt_id() -> str:
    return "AP-" + secrets.token_hex(6)


def verify(
    repo: Path,
    base: str,
    head: str,
    test_command: str,
    proof_commands: list[str] | None = None,
    claims: list[str] | None = None,
    timeout: int = 600,
) -> VerificationReceipt:
    proof_commands = proof_commands or []
    claims = claims or []
    base_dir = repo / ".agentproof-base"
    head_dir = repo / ".agentproof-head"
    try:
        checkout(repo, base, base_dir)
        checkout(repo, head, head_dir)
        base_tests = run_command(test_command, base_dir, timeout)
        head_tests = run_command(test_command, head_dir, timeout)
        proof_results: list[ProofTestResult] = []
        for command in proof_commands:
            base_run = run_command(command, base_dir, timeout)
            head_run = run_command(command, head_dir, timeout)
            proof_results.append(compare_proof_test(command, base_run, head_run))
    finally:
        remove_worktree(repo, base_dir)
        remove_worktree(repo, head_dir)

    findings, diff_evidence = audit_diff(repo, base, head)
    blocking_findings = [f for f in findings if f.severity == "high"]
    proof_failures = [p for p in proof_results if p.status != "PROVEN"]
    if not head_tests.passed or blocking_findings or any(p.status in {"NOT_FIXED", "REGRESSION"} for p in proof_results):
        verdict = "BLOCKED"
    elif proof_failures:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "VERIFIED"

    receipt = VerificationReceipt(
        schema_version="agentproof.receipt/v1",
        receipt_id=_receipt_id(),
        created_at=datetime.now(timezone.utc).isoformat(),
        verifier_version=VERSION,
        verdict=verdict,
        base=base,
        head=head,
        claims=claims,
        evidence={"diff": diff_evidence, "head_tests_passed": head_tests.passed},
        findings=findings,
        test_runs={"base": base_tests, "head": head_tests},
        proof_tests=proof_results,
        environment=_environment(),
    )
    canonical = json.dumps(receipt.unsigned_dict(), sort_keys=True, separators=(",", ":")).encode()
    receipt.receipt_sha256 = hashlib.sha256(canonical).hexdigest()
    return receipt

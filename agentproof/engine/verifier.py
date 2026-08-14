from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__
from ..adapters.discover import discover_canonical_command
from ..checks.ci.github_actions import detect_ci_integrity
from ..checks.common import changed_files, diff_by_file
from ..checks.contracts.json_contract import compare_json_contracts
from ..checks.dependencies.check import detect_dependency_integrity
from ..checks.tests.assertions import detect_assertion_weakening
from ..checks.tests.discovery import (
    detect_deleted_tests,
    detect_discovery_reduction,
    detect_test_command_reduction,
)
from ..checks.tests.focus import detect_focused_tests
from ..checks.tests.mock import detect_mock_weakening
from ..checks.tests.skips import detect_added_skips
from ..checks.tests.snapshots import detect_coverage_and_snapshots
from ..engine.environment import fingerprint
from ..engine.evidence import EvidenceGraph, EvidenceNode
from ..engine.executor import execute
from ..engine.worktrees import WorktreeManager
from ..models import ClaimResult, Finding, TestRun, VerificationReceipt
from ..policy.evaluator import evaluate_findings
from ..proof.tests import discover_new_tests, run_proof_tests, run_transplanted_proofs

VERSION = __version__


def _test_run(run: Any) -> TestRun:
    return TestRun(
        command=run.command,
        cwd=run.cwd,
        exit_code=run.exit_code,
        duration_seconds=run.duration_seconds,
        output_tail=run.output_tail,
        stdout_hash=run.stdout_hash,
        stderr_hash=run.stderr_hash,
        test_counts=run.test_counts,
        environment_fingerprint=run.environment_fingerprint,
        commit_sha=run.commit_sha,
    )


def _claims(requested: list[str], base: TestRun, head: TestRun, proof_results: list[dict[str, object]], findings: list[Finding]) -> list[ClaimResult]:
    normalized = {claim.lower().replace(" ", "_"): claim for claim in requested}
    results: list[ClaimResult] = []
    if not requested or any("test" in key and "pass" in key for key in normalized):
        results.append(ClaimResult("tests_pass", "PROVEN" if head.passed else "CONTRADICTED", [f"HEAD exit code: {head.exit_code}"], "The canonical test command was independently executed on HEAD."))
    if not requested or any("regression" in key for key in normalized):
        proven = [result for result in proof_results if result.get("status") == "PROVEN"]
        contradicted = [result for result in proof_results if result.get("status") in {"NOT_FIXED", "REGRESSION", "UNREPRODUCIBLE"}]
        status = "PROVEN" if proven else "CONTRADICTED" if contradicted else "UNPROVEN"
        results.append(ClaimResult("regression_test_added", status, [str(item.get("command")) for item in proof_results], "A regression claim requires BASE failure and HEAD success."))
    if any("bug" in key and "fix" in key for key in normalized):
        results.append(ClaimResult("bug_fixed", "SUPPORTED" if head.passed and not any(f.rule in {"AP203", "AP202"} for f in findings) else "CONTRADICTED", [], "Behavior is supported by independent execution; it is not a formal proof of all bug semantics."))
    if any("backward" in key or "compatible" in key for key in normalized):
        results.append(ClaimResult("backwards_compatible", "UNPROVEN", [], "No public API snapshot was supplied for this verification run."))
    return results


def verify_core(repo: Path, base: str, head: str, test_command: str | None = None, proof_commands: list[str] | None = None, claims: list[str] | None = None, policy: dict[str, Any] | None = None, timeout: int = 600, network_mode: str = "deny", auto_proof: bool = True) -> VerificationReceipt:
    proof_commands = proof_commands or []
    claims = claims or []
    policy = policy or {}
    changed = changed_files(repo, base, head)
    diff = diff_by_file(repo, base, head)
    command = discover_canonical_command(repo, test_command)
    environment: dict[str, Any] = {}
    findings: list[Finding] = []
    findings.extend(detect_added_skips(diff))
    findings.extend(detect_focused_tests(diff))
    findings.extend(detect_mock_weakening(diff))
    findings.extend(detect_deleted_tests(diff))
    findings.extend(detect_discovery_reduction(diff))
    findings.extend(detect_test_command_reduction(diff))
    findings.extend(detect_coverage_and_snapshots(diff))
    findings.extend(detect_ci_integrity(diff))
    findings.extend(detect_dependency_integrity(changed, diff))

    graph = EvidenceGraph()
    base_run: TestRun
    head_run: TestRun
    with WorktreeManager(repo) as worktrees:
        base_path = worktrees.create(base, "base")
        head_path = worktrees.create(head, "head")
        runner_type = "github-actions" if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" else "local"
        environment = fingerprint(head_path, network_mode=network_mode, runner_type=runner_type)
        base_evidence = execute(command, base_path, "BASE", base, str(environment.get("fingerprint", "")), timeout)
        head_evidence = execute(command, head_path, "HEAD", head, str(environment.get("fingerprint", "")), timeout)
        base_run, head_run = _test_run(base_evidence), _test_run(head_evidence)
        findings.extend(detect_assertion_weakening(base_path, head_path, changed))
        for relative in changed:
            contract_candidate = relative.endswith(("contract.json", ".schema.json")) or "/contracts/" in relative or "/schemas/" in relative
            if contract_candidate and (base_path / relative).is_file() and (head_path / relative).is_file():
                findings.extend(compare_json_contracts(base_path / relative, head_path / relative, relative))

    proof_results, proof_findings = run_proof_tests(repo, base, head, proof_commands, timeout, str(environment.get("fingerprint", ""))) if proof_commands else ([], [])
    findings.extend(proof_findings)
    if auto_proof:
        discovered = discover_new_tests(changed)
        transplanted, transplanted_findings = run_transplanted_proofs(repo, base, head, discovered, command, timeout, str(environment.get("fingerprint", ""))) if discovered else ([], [])
        proof_results.extend(transplanted)
        findings.extend(transplanted_findings)

    security_policy = policy.get("security", {}) if policy else {}
    if security_policy.get("isolated_runner_required") and os.environ.get("AGENTPROOF_ISOLATED_RUNNER", "").lower() != "true":
        findings.append(Finding("AP502", "high", "The selected policy requires an isolated runner, but the current runner did not attest isolation.", evidence=["Set AGENTPROOF_ISOLATED_RUNNER=true only from a trusted isolated runner."]))
    receipt_policy = policy.get("receipt", {}) if policy else {}
    if receipt_policy.get("signature_required") and not os.environ.get("AGENTPROOF_ED25519_PRIVATE_KEY"):
        findings.append(Finding("AP501", "high", "The selected policy requires a signed receipt, but no signing key is available.", evidence=["Provide AGENTPROOF_ED25519_PRIVATE_KEY from a trusted signing step."]))
    findings = evaluate_findings(findings, policy) if policy else findings
    blocking = [finding for finding in findings if finding.metadata.get("policy_action", "block") == "block"]
    security_blockers = [finding for finding in findings if finding.rule in {"AP501", "AP502"}]
    proof_blockers = [result for result in proof_results if result.get("status") in {"NOT_FIXED", "REGRESSION", "UNREPRODUCIBLE"}]
    require_proof = bool(policy.get("verification", {}).get("require_proof_tests", False))
    if not head_run.passed or blocking or security_blockers or proof_blockers or (require_proof and not proof_results):
        verdict = "BLOCKED"
    elif any(result.get("status") == "INCONCLUSIVE" for result in proof_results):
        verdict = "INCONCLUSIVE"
    else:
        verdict = "VERIFIED"

    receipt = VerificationReceipt(
        schema_version="agentproof.receipt/v1",
        receipt_id="AP-" + secrets.token_hex(6),
        created_at=datetime.now(timezone.utc).isoformat(),
        verifier_version=VERSION,
        verdict=verdict,
        base=base,
        head=head,
        claims=claims,
        evidence={"changed_files": changed, "test_command": command, "head_tests_passed": head_run.passed},
        findings=findings,
        test_runs={"base": base_run, "head": head_run},
        proof_tests=[],
        environment=environment,
        subject={"repository": str(repo), "base_sha": base, "head_sha": head},
        policy=policy,
        evidence_graph=graph.to_dict(),
    )
    receipt.proof_tests = []
    for result in proof_results:
        receipt.proof_tests.append(result)
    receipt.evidence_graph = {
        "nodes": [asdict(EvidenceNode("base-tests", "test_run", asdict(base_run))), asdict(EvidenceNode("head-tests", "test_run", asdict(head_run)))],
        "edges": [{"source": "head-tests", "target": "receipt", "relation": "supports"}],
    }
    receipt.evidence["claims"] = [asdict(claim) for claim in _claims(claims, base_run, head_run, proof_results, findings)]
    private_key = os.environ.get("AGENTPROOF_ED25519_PRIVATE_KEY")
    if receipt_policy.get("signature_required") and private_key:
        from ..receipt.sign import sign_payload
        receipt.signature = sign_payload(receipt.stable_unsigned_dict(), bytes.fromhex(private_key))
    canonical = json.dumps(receipt.stable_unsigned_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    receipt.receipt_sha256 = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return receipt

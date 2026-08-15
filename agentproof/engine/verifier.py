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
from ..adapters.discover import discover_canonical_command, discover_setup_command
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
from ..policy.evaluator import evaluate_findings, proof_mode
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
        dependency_lock_hash=run.dependency_lock_hash,
    )


def _claims(requested: list[str], base: TestRun, head: TestRun, proof_results: list[dict[str, object]], findings: list[Finding], setup_failed: bool = False) -> list[ClaimResult]:
    normalized = {claim.lower().replace(" ", "_"): claim for claim in requested}
    results: list[ClaimResult] = []
    if not requested or any("test" in key and "pass" in key for key in normalized):
        if setup_failed:
            results.append(ClaimResult("tests_pass", "UNPROVEN", ["Setup failed before the canonical test command could run."], "The repository could not be reproduced because setup failed."))
        else:
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


def verify_core(repo: Path, base: str, head: str, test_command: str | None = None, proof_commands: list[str] | None = None, claims: list[str] | None = None, policy: dict[str, Any] | None = None, timeout: int = 600, network_mode: str = "deny", auto_proof: bool = True, setup_command: str | None = None) -> VerificationReceipt:
    proof_commands = proof_commands or []
    claims = claims or []
    policy = policy or {}
    changed = changed_files(repo, base, head)
    diff = diff_by_file(repo, base, head)
    command = discover_canonical_command(repo, test_command)
    environment: dict[str, Any] = {}
    base_environment: dict[str, Any] = {}
    head_environment: dict[str, Any] = {}
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
    setup_runs: dict[str, TestRun] = {}
    setup_failed = False
    with WorktreeManager(repo) as worktrees:
        base_path = worktrees.create(base, "base")
        head_path = worktrees.create(head, "head")
        runner_type = "github-actions" if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" else "local"
        base_environment = fingerprint(base_path, network_mode=network_mode, runner_type=runner_type)
        head_environment = fingerprint(head_path, network_mode=network_mode, runner_type=runner_type)
        environment = {
            "base": base_environment,
            "head": head_environment,
            "comparison": {
                "toolchain_equal": base_environment.get("fingerprint") == head_environment.get("fingerprint"),
                "runner_equal": base_environment.get("runner_type") == head_environment.get("runner_type"),
                "lockfiles_equal": base_environment.get("dependency_lock_hash") == head_environment.get("dependency_lock_hash"),
            },
        }
        base_setup_command = discover_setup_command(base_path, setup_command)
        head_setup_command = discover_setup_command(head_path, setup_command)
        base_setup = execute(base_setup_command, base_path, "BASE_SETUP", base, str(base_environment.get("fingerprint", "")), timeout, str(base_environment.get("dependency_lock_hash", ""))) if base_setup_command else None
        head_setup = execute(head_setup_command, head_path, "HEAD_SETUP", head, str(head_environment.get("fingerprint", "")), timeout, str(head_environment.get("dependency_lock_hash", ""))) if head_setup_command else None
        if base_setup:
            setup_runs["base"] = _test_run(base_setup)
        if head_setup:
            setup_runs["head"] = _test_run(head_setup)
        setup_failed = bool((base_setup and not base_setup.passed) or (head_setup and not head_setup.passed))
        if base_setup and not base_setup.passed:
            base_run = _test_run(execute("printf '%s' 'AgentProof: setup failed; test command not run'", base_path, "BASE", base, str(base_environment.get("fingerprint", "")), timeout=1, dependency_lock_hash=str(base_environment.get("dependency_lock_hash", ""))))
            base_run.exit_code = 125
            base_run.output_tail = base_setup.output_tail
        else:
            base_evidence = execute(command, base_path, "BASE", base, str(base_environment.get("fingerprint", "")), timeout, str(base_environment.get("dependency_lock_hash", "")))
            base_run = _test_run(base_evidence)
        if head_setup and not head_setup.passed:
            head_run = _test_run(execute("printf '%s' 'AgentProof: setup failed; test command not run'", head_path, "HEAD", head, str(head_environment.get("fingerprint", "")), timeout=1, dependency_lock_hash=str(head_environment.get("dependency_lock_hash", ""))))
            head_run.exit_code = 125
            head_run.output_tail = head_setup.output_tail
        else:
            head_evidence = execute(command, head_path, "HEAD", head, str(head_environment.get("fingerprint", "")), timeout, str(head_environment.get("dependency_lock_hash", "")))
            head_run = _test_run(head_evidence)
        findings.extend(detect_assertion_weakening(base_path, head_path, changed))
        for relative in changed:
            contract_candidate = relative.endswith(("contract.json", ".schema.json")) or "/contracts/" in relative or "/schemas/" in relative
            if contract_candidate and (base_path / relative).is_file() and (head_path / relative).is_file():
                findings.extend(compare_json_contracts(base_path / relative, head_path / relative, relative))

    discovered = discover_new_tests(changed) if auto_proof else []
    mode = proof_mode(policy)
    claim_requires_proof = any(any(token in claim.lower() for token in ("bug", "regression", "fix")) for claim in claims)
    proof_required = bool(proof_commands) or mode == "required" or (mode == "auto" and bool(discovered or claim_requires_proof))
    proof_results: list[dict[str, object]] = []
    proof_findings: list[Finding] = []
    proof_setup_runs: dict[str, Any] = {}
    if proof_commands:
        proof_results, proof_findings, proof_setup_runs = run_proof_tests(repo, base, head, proof_commands, timeout, base_environment, head_environment, setup_command)
        setup_runs.update({name: _test_run(run) for name, run in proof_setup_runs.items()})
    findings.extend(proof_findings)
    if setup_failed:
        findings.append(Finding("AP204", "medium", "Repository setup failed before canonical tests could run; reproducibility is unproven.", category="reproducibility", evidence=[run.output_tail for run in setup_runs.values() if run.exit_code != 0]))
    if auto_proof and discovered:
        transplanted, transplanted_findings, transplanted_setup_runs = run_transplanted_proofs(repo, base, head, discovered, command, timeout, base_environment, head_environment, setup_command)
        proof_results.extend(transplanted)
        findings.extend(transplanted_findings)
        setup_runs.update({name: _test_run(run) for name, run in transplanted_setup_runs.items()})

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
    if setup_failed and not blocking and not security_blockers:
        verdict = "INCONCLUSIVE"
    elif not head_run.passed or blocking or security_blockers or proof_blockers or (proof_required and not proof_results):
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
        evidence={"changed_files": changed, "test_command": command, "setup_command": setup_command or "auto", "setup_failed": setup_failed, "proof_tests_mode": mode, "proof_tests_required": proof_required, "head_tests_passed": head_run.passed},
        findings=findings,
        test_runs={"base": base_run, "head": head_run},
        setup_runs=setup_runs,
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
        "nodes": [
            *[asdict(EvidenceNode(f"{name}-setup", "setup_run", asdict(run))) for name, run in setup_runs.items()],
            asdict(EvidenceNode("base-tests", "test_run", asdict(base_run))),
            asdict(EvidenceNode("head-tests", "test_run", asdict(head_run))),
        ],
        "edges": [
            *[{"source": f"{name}-setup", "target": f"{name}-tests", "relation": "precedes"} for name in setup_runs],
            {"source": "head-tests", "target": "receipt", "relation": "supports"},
        ],
    }
    receipt.evidence["claims"] = [asdict(claim) for claim in _claims(claims, base_run, head_run, proof_results, findings, setup_failed)]
    private_key = os.environ.get("AGENTPROOF_ED25519_PRIVATE_KEY")
    if receipt_policy.get("signature_required") and private_key:
        from ..receipt.sign import sign_payload
        receipt.signature = sign_payload(receipt.stable_unsigned_dict(), bytes.fromhex(private_key))
    canonical = json.dumps(receipt.stable_unsigned_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    receipt.receipt_sha256 = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return receipt

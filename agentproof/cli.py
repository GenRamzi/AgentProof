from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .adapters.discover import CommandDiscoveryError, discover_canonical_command
from .engine.verifier import verify_core
from .policy.evaluator import load_policy, preset
from .receipt.verify import verify_receipt
from .reporters.render import render_markdown, render_sarif
from .rules import RULES


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def discover_refs(repo: Path) -> tuple[str, str]:
    head = _git(repo, "rev-parse", "HEAD")
    for candidate in ("origin/main", "main", "origin/master", "master"):
        result = subprocess.run(["git", "rev-parse", "--verify", candidate], cwd=repo, text=True, capture_output=True, check=False)
        if result.returncode == 0 and _git(repo, "merge-base", candidate, head) != head:
            return _git(repo, "merge-base", candidate, head), head
    parents = _git(repo, "rev-list", "--parents", "-n", "1", head).split()
    return (parents[1] if len(parents) > 1 else head), head


def write_outputs(receipt, json_path: Path, markdown_path: Path, sarif_path: Path | None = None) -> None:
    json_path.write_text(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(render_markdown(receipt), encoding="utf-8")
    if sarif_path:
        sarif_path.write_text(json.dumps(render_sarif(receipt), indent=2), encoding="utf-8")


def cmd_init(path: Path) -> int:
    target = path / "agentproof.yml"
    if target.exists():
        print(f"Already exists: {target}")
        return 0
    target.write_text("""version: 1\n\nverification:\n  test_command: null\n  require_tests: true\n  require_proof_tests: false\n\nintegrity:\n  deleted_tests: warning\n  new_skips: warning\n  assertion_weakening: review\n  ci_changes: review\n\nnetwork:\n  mode: deny\n  domains: []\n\nreceipt:\n  signature_required: false\n""", encoding="utf-8")
    print(f"Created {target}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    policy_path = args.policy or (repo / "agentproof.yml" if (repo / "agentproof.yml").is_file() else None)
    policy = load_policy(policy_path, args.policy_preset)
    configured_command = args.test_command
    if configured_command is None and policy.get("verification", {}).get("test_command"):
        configured_command = policy["verification"]["test_command"]
    base, head = args.base, args.head
    if not base or not head:
        base, head = discover_refs(repo)
    receipt = verify_core(repo, base, head, configured_command, args.proof_test, args.claim, policy, args.timeout, policy.get("network", {}).get("mode", "deny"), not args.no_auto_proof)
    write_outputs(receipt, args.json, args.markdown, args.sarif)
    print(render_markdown(receipt))
    return 0 if receipt.verdict == "VERIFIED" else 1


def cmd_proof(args: argparse.Namespace) -> int:
    args.claim = args.claim or ["Added regression coverage"]
    args.proof_test = args.proof_test or []
    return cmd_verify(args)


def cmd_audit(args: argparse.Namespace) -> int:
    args.proof_test = []
    args.claim = []
    args.no_auto_proof = True
    return cmd_verify(args)


def cmd_receipt_verify(path: Path) -> int:
    valid, expected, actual = verify_receipt(path)
    print(json.dumps({"valid": valid, "expected": expected, "actual": actual}, indent=2))
    return 0 if valid else 1


def cmd_explain(rule_id: str) -> int:
    rule = RULES.get(rule_id.upper())
    if not rule:
        print(f"Unknown rule: {rule_id}", file=sys.stderr)
        return 1
    print(json.dumps({"id": rule.rule_id, "title": rule.title, "severity": rule.default_severity, "description": rule.description}, indent=2))
    return 0


def cmd_doctor(repo: Path) -> int:
    checks = {"git": False, "python": True, "test_command": False, "policy": (repo / "agentproof.yml").is_file()}
    try:
        _git(repo, "rev-parse", "--show-toplevel")
        checks["git"] = True
    except RuntimeError:
        pass
    try:
        discover_canonical_command(repo)
        checks["test_command"] = True
    except CommandDiscoveryError:
        pass
    print(json.dumps({"repository": str(repo), "checks": checks, "ready": all(checks.values())}, indent=2))
    return 0 if all(checks.values()) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentproof", description="Independent verification for AI-generated software.")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create agentproof.yml")
    init.add_argument("--path", type=Path, default=Path("."))

    def verification_parser(name: str, help_text: str) -> argparse.ArgumentParser:
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--repo", type=Path, default=Path("."))
        item.add_argument("--base")
        item.add_argument("--head")
        item.add_argument("--test-command")
        item.add_argument("--proof-test", action="append", default=[])
        item.add_argument("--claim", action="append", default=[])
        item.add_argument("--policy", type=Path)
        item.add_argument("--policy-preset", choices=sorted(preset(name).get("version", 1) for name in []) if False else ["default", "strict", "enterprise"], default="default")
        item.add_argument("--timeout", type=int, default=600)
        item.add_argument("--json", type=Path, default=Path("agentproof-receipt.json"))
        item.add_argument("--markdown", type=Path, default=Path("agentproof-report.md"))
        item.add_argument("--sarif", type=Path)
        item.add_argument("--no-auto-proof", action="store_true")
        return item

    verification_parser("verify", "run independent verification")
    verification_parser("proof", "run proof-test verification")
    verification_parser("audit", "run integrity-only audit")
    receipt = sub.add_parser("receipt", help="receipt operations")
    receipt_sub = receipt.add_subparsers(dest="receipt_command", required=True)
    receipt_verify = receipt_sub.add_parser("verify", help="verify receipt digest")
    receipt_verify.add_argument("path", type=Path)
    explain = sub.add_parser("explain", help="explain a stable rule ID")
    explain.add_argument("rule_id")
    doctor = sub.add_parser("doctor", help="check local readiness")
    doctor.add_argument("--repo", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return cmd_init(args.path.resolve())
    if args.command == "receipt":
        return cmd_receipt_verify(args.path) if args.receipt_command == "verify" else 1
    if args.command == "explain":
        return cmd_explain(args.rule_id)
    if args.command == "doctor":
        return cmd_doctor(args.repo.resolve())
    try:
        if args.command == "proof":
            return cmd_proof(args)
        if args.command == "audit":
            return cmd_audit(args)
        return cmd_verify(args)
    except (RuntimeError, CommandDiscoveryError, FileNotFoundError, ValueError) as exc:
        print(f"AgentProof error: {exc}", file=sys.stderr)
        return 2

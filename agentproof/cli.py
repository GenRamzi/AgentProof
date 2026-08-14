from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .models import VerificationReceipt
from .verifier import verify


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _receipt_from_dict(data: dict) -> VerificationReceipt:
    # Receipt verification only needs the canonical payload, so retain the raw dict below.
    return VerificationReceipt(**data)


def render_markdown(receipt: VerificationReceipt) -> str:
    lines = [
        f"# AgentProof {receipt.verdict}",
        "",
        f"**Receipt:** `{receipt.receipt_id}`  ",
        f"**Base:** `{receipt.base}`  ",
        f"**Head:** `{receipt.head}`  ",
        f"**Verifier:** `{receipt.verifier_version}`",
        "",
        "## Independent test runs",
        "",
        "| Revision | Result | Exit code | Duration |",
        "|---|---:|---:|---:|",
    ]
    for name in ("base", "head"):
        run = receipt.test_runs[name]
        lines.append(f"| {name} | {'PASS' if run.passed else 'FAIL'} | {run.exit_code} | {run.duration_seconds}s |")
    lines += ["", "## Proof tests", ""]
    if receipt.proof_tests:
        lines += ["| Command | Base | PR | Status |", "|---|---:|---:|---|"]
        for proof in receipt.proof_tests:
            lines.append(f"| `{proof.command}` | {'PASS' if proof.base.passed else 'FAIL'} | {'PASS' if proof.head.passed else 'FAIL'} | **{proof.status}** |")
            lines.append(f"|  |  |  | {proof.interpretation} |")
    else:
        lines.append("No proof-test command was supplied. The result covers reproducible test execution and diff integrity checks only.")
    lines += ["", "## Findings", ""]
    if receipt.findings:
        for finding in receipt.findings:
            lines.append(f"- **{finding.severity.upper()} — {finding.rule}:** {finding.message}")
            if finding.evidence:
                lines.append(f"  Evidence: `{'; '.join(finding.evidence)}`")
    else:
        lines.append("No suspicious test-integrity findings were detected by the configured rules.")
    lines += ["", "## Receipt integrity", "", f"SHA-256: `{receipt.receipt_sha256}`", ""]
    return "\n".join(lines)


def verify_receipt(path: Path) -> int:
    data = _load(path)
    expected = data.get("receipt_sha256", "")
    unsigned = dict(data)
    unsigned.pop("receipt_sha256", None)
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(canonical).hexdigest()
    valid = expected == actual
    print(json.dumps({"valid": valid, "expected": expected, "actual": actual}, indent=2))
    return 0 if valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentproof", description="Independent verification for AI-generated software.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="verify a base revision against a PR revision")
    verify_parser.add_argument("--repo", type=Path, default=Path("."))
    verify_parser.add_argument("--base", required=True)
    verify_parser.add_argument("--head", required=True)
    verify_parser.add_argument("--test-command", default="pytest -q")
    verify_parser.add_argument("--proof-test", action="append", default=[])
    verify_parser.add_argument("--claim", action="append", default=[])
    verify_parser.add_argument("--timeout", type=int, default=600)
    verify_parser.add_argument("--json", type=Path, default=Path("agentproof-receipt.json"))
    verify_parser.add_argument("--markdown", type=Path, default=Path("agentproof-report.md"))

    receipt_parser = subparsers.add_parser("verify-receipt", help="verify a receipt SHA-256 digest")
    receipt_parser.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    if args.command == "verify-receipt":
        return verify_receipt(args.path)

    try:
        receipt = verify(args.repo.resolve(), args.base, args.head, args.test_command, args.proof_test, args.claim, args.timeout)
    except subprocess.CalledProcessError as exc:
        print(f"AgentProof setup error: {exc}", file=sys.stderr)
        return 2
    args.json.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
    args.markdown.write_text(render_markdown(receipt), encoding="utf-8")
    print(render_markdown(receipt))
    return 0 if receipt.verdict == "VERIFIED" else 1

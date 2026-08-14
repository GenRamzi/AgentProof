from __future__ import annotations

import json
from typing import Any


def render_markdown(receipt: Any) -> str:
    data = receipt.to_dict() if hasattr(receipt, "to_dict") else receipt
    verdict = data.get("verdict", "UNKNOWN")
    lines = [
        "# AgentProof",
        "",
        "**Independent verification for AI-generated software.**",
        "",
        f"## Verdict: `{verdict}`",
        "",
        f"**Receipt:** `{data.get('receipt_id', 'unknown')}`  ",
        f"**Base:** `{data.get('base') or data.get('subject', {}).get('base_sha', 'unknown')}`  ",
        f"**Head:** `{data.get('head') or data.get('subject', {}).get('head_sha', 'unknown')}`",
        "",
        "## Claims",
        "",
        "| Claim | Status | Evidence |",
        "|---|---|---|",
    ]
    claims = data.get("evidence", {}).get("claims", []) or data.get("claims", [])
    if claims:
        for claim in claims:
            if isinstance(claim, str):
                lines.append(f"| {claim} | — | — |")
            else:
                lines.append(f"| `{claim.get('type', 'claim')}` | **{claim.get('status', 'UNPROVEN')}** | {'; '.join(claim.get('evidence', []))} |")
    else:
        lines.append("| No claims supplied | `NOT_APPLICABLE` | — |")
    lines += ["", "## Proof Tests", "", "| Test | BASE | HEAD | Status |", "|---|---:|---:|---|"]
    proof_tests = data.get("proof_tests", [])
    if proof_tests:
        for proof in proof_tests:
            base = proof.get("base", {})
            head = proof.get("head", {})
            lines.append(f"| `{proof.get('command', proof.get('test_file', 'proof'))}` | {'PASS' if base.get('exit_code') == 0 else 'FAIL'} | {'PASS' if head.get('exit_code') == 0 else 'FAIL'} | **{proof.get('status', 'UNKNOWN')}** |")
            if proof.get("interpretation"):
                lines.append(f"|  |  |  | {proof['interpretation']} |")
    else:
        lines.append("| No proof tests supplied or discovered | — | — | `NOT_APPLICABLE` |")
    lines += ["", "## Integrity", ""]
    findings = data.get("findings", []) or data.get("integrity_findings", [])
    if findings:
        for finding in findings:
            lines.append(f"- **{finding.get('rule', finding.get('rule_id', 'AP000'))} — {finding.get('severity', 'info').upper()}:** {finding.get('message', '')}")
            evidence = finding.get("evidence", [])
            if evidence:
                lines.append(f"  Evidence: `{'; '.join(evidence[:5])}`")
    else:
        lines.append("- No integrity violations detected by the configured rules.")
    lines += ["", "## Test Runs", "", "| Revision | Result | Exit | Duration | Test counts |", "|---|---:|---:|---:|---|"]
    runs = data.get("test_runs", {})
    if isinstance(runs, dict):
        iterator = runs.items()
    else:
        iterator = ((run.get("revision", "unknown"), run) for run in runs)
    for name, run in iterator:
        lines.append(f"| {name} | {'PASS' if run.get('exit_code') == 0 else 'FAIL'} | {run.get('exit_code')} | {run.get('duration_seconds', 0)}s | `{run.get('test_counts', {})}` |")
    lines += ["", "## Receipt", "", f"Digest: `{data.get('receipt_sha256') or data.get('digest', '')}`", ""]
    return "\n".join(lines)


def render_sarif(receipt: Any) -> dict[str, Any]:
    data = receipt.to_dict() if hasattr(receipt, "to_dict") else receipt
    results = []
    for finding in data.get("findings", []) or data.get("integrity_findings", []):
        results.append({
            "ruleId": finding.get("rule", finding.get("rule_id", "AP000")),
            "level": "error" if finding.get("severity") == "high" else "warning" if finding.get("severity") == "medium" else "note",
            "message": {"text": finding.get("message", "")},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": path}, "region": {"startLine": finding.get("line", 1)}}} for path in finding.get("files", [])[:5]],
        })
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "runs": [{"tool": {"driver": {"name": "AgentProof", "version": data.get("verifier_version", "0.2.0")}}, "results": results}]}

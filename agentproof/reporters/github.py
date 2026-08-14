from __future__ import annotations


def check_run_payload(receipt) -> dict:
    data = receipt.to_dict() if hasattr(receipt, "to_dict") else receipt
    conclusion = "success" if data.get("verdict") == "VERIFIED" else "failure"
    findings = data.get("findings", []) or data.get("integrity_findings", [])
    annotations = []
    for finding in findings:
        for path in finding.get("files", [])[:10]:
            annotations.append({"path": path, "start_line": finding.get("line") or 1, "end_line": finding.get("line") or 1, "annotation_level": "failure" if finding.get("severity") == "high" else "warning", "message": f"{finding.get('rule', 'AP000')}: {finding.get('message', '')}"})
    return {"name": "AgentProof / Verification", "status": "completed", "conclusion": conclusion, "output": {"title": f"AgentProof {data.get('verdict')}", "summary": f"Receipt {data.get('receipt_id', 'unknown')}", "annotations": annotations}}

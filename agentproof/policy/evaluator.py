from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
    "verification": {"require_tests": True, "require_proof_tests": False},
    "integrity": {"deleted_tests": "warning", "new_skips": "warning", "assertion_weakening": "review", "ci_changes": "review"},
    "coverage": {"minimum_delta": 0},
    "dependencies": {"lockfile_changes": "review"},
    "network": {"mode": "deny", "domains": []},
    "receipt": {"signature_required": False},
}

PRESET_NAMES = {"default", "strict", "enterprise"}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def preset(name: str) -> dict[str, Any]:
    if name == "default":
        return _merge(DEFAULT_POLICY, {})
    if name == "strict":
        return _merge(DEFAULT_POLICY, {"verification": {"require_proof_tests": True}, "integrity": {"deleted_tests": "block", "new_skips": "block", "assertion_weakening": "block", "ci_changes": "block"}, "dependencies": {"lockfile_changes": "block"}})
    if name == "enterprise":
        return _merge(preset("strict"), {"network": {"mode": "deny"}, "receipt": {"signature_required": True}, "security": {"isolated_runner_required": True}})
    raise ValueError(f"Unknown policy preset: {name}")


def load_policy(path: Path | None = None, name: str = "default") -> dict[str, Any]:
    policy = preset(name)
    if path is None:
        return policy
    if not path.is_file():
        raise FileNotFoundError(path)
    if yaml is None:
        raise RuntimeError("PyYAML is required to load agentproof.yml")
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Policy root must be a mapping")
    return _merge(policy, parsed)


def action_for(policy: dict[str, Any], rule_id: str) -> str:
    mapping = {
        "AP001": "deleted_tests",
        "AP002": "new_skips",
        "AP003": "new_skips",
        "AP004": "ci_changes",
        "AP005": "assertion_weakening",
        "AP006": "coverage_exclusion",
        "AP007": "snapshot_overwrite",
        "AP101": "ci_changes",
        "AP102": "ci_changes",
        "AP103": "ci_changes",
        "AP104": "ci_changes",
        "AP301": "dependency_expansion",
        "AP302": "lockfile_changes",
        "AP401": "api_contract_changes",
    }
    return str(policy.get("integrity", {}).get(mapping.get(rule_id, ""), "warning"))


def evaluate_findings(findings: list[Any], policy: dict[str, Any]) -> list[Any]:
    for finding in findings:
        action = action_for(policy, finding.rule)
        finding.metadata = getattr(finding, "metadata", {})
        finding.metadata["policy_action"] = action
        if action == "block":
            finding.severity = "high"
        elif action == "review" and finding.severity == "low":
            finding.severity = "medium"
    return findings

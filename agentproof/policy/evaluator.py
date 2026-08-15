from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
    "verification": {"require_tests": True, "proof_tests": "auto"},
    "integrity": {"deleted_tests": "warning", "new_skips": "warning", "assertion_weakening": "review", "ci_changes": "review"},
    "coverage": {"minimum_delta": 0},
    "dependencies": {"lockfile_changes": "review"},
    "network": {"mode": "deny", "domains": []},
    "receipt": {"signature_required": False},
}

PRESET_NAMES = {"default", "strict", "enterprise"}
VALID_ACTIONS = {"ignore", "warning", "review", "block"}
VALID_PROOF_MODES = {"off", "auto", "required"}


def _safe_action(value: Any) -> str:
    action = str(value)
    return action if action in VALID_ACTIONS else "warning"


def _normalize_proof_mode(verification: dict[str, Any]) -> None:
    mode = verification.get("proof_tests")
    if mode is None and "require_proof_tests" in verification:
        mode = "required" if verification["require_proof_tests"] else "off"
    if isinstance(mode, bool):
        mode = "required" if mode else "off"
    verification["proof_tests"] = mode if mode in VALID_PROOF_MODES else "warning"
    verification.pop("require_proof_tests", None)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _normalized(policy: dict[str, Any]) -> dict[str, Any]:
    result = _merge({}, policy)
    verification = result.setdefault("verification", {})
    if not isinstance(verification, dict):
        verification = result["verification"] = {}
    _normalize_proof_mode(verification)
    return result


def preset(name: str) -> dict[str, Any]:
    if name == "default":
        return _normalized(_merge(DEFAULT_POLICY, {}))
    if name == "strict":
        return _normalized(_merge(DEFAULT_POLICY, {"verification": {"proof_tests": "auto"}, "integrity": {"deleted_tests": "block", "new_skips": "block", "assertion_weakening": "block", "ci_changes": "block"}, "dependencies": {"lockfile_changes": "block"}}))
    if name == "enterprise":
        return _normalized(_merge(preset("strict"), {"network": {"mode": "deny"}, "receipt": {"signature_required": True}, "security": {"isolated_runner_required": True}}))
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
        raise TypeError("Policy root must be a mapping")
    return _normalized(_merge(policy, parsed))


def proof_mode(policy: dict[str, Any]) -> str:
    verification = policy.get("verification", {})
    if not isinstance(verification, dict):
        return "warning"
    mode = verification.get("proof_tests", "auto")
    return mode if mode in VALID_PROOF_MODES else "warning"


def action_for(policy: dict[str, Any], rule_id: str) -> str:
    integrity = {
        "AP001": "deleted_tests", "AP002": "new_skips", "AP003": "new_skips", "AP004": "discovery_reduction", "AP005": "assertion_weakening", "AP006": "coverage_exclusion",
        "AP007": "snapshot_overwrite", "AP008": "mock_weakening", "AP101": "ci_changes", "AP102": "ci_changes", "AP103": "ci_changes", "AP104": "ci_changes", "AP401": "api_contract_changes",
    }
    dependency = {"AP301": "dependency_expansion", "AP302": "lockfile_changes"}
    if rule_id in dependency:
        return _safe_action(policy.get("dependencies", {}).get(dependency[rule_id], "review"))
    if rule_id == "AP006":
        return _safe_action(policy.get("coverage", {}).get("coverage_exclusion", policy.get("integrity", {}).get("coverage_exclusion", "review")))
    if rule_id in integrity:
        return _safe_action(policy.get("integrity", {}).get(integrity[rule_id], "warning"))
    return "warning"


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

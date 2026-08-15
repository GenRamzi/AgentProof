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
VALID_NETWORK_MODES = {"deny", "install-only", "allow"}
ALLOWED_TOP_LEVEL = {"version", "verification", "integrity", "coverage", "dependencies", "network", "receipt", "security"}
ALLOWED_VERIFICATION = {"test_command", "setup_command", "require_tests", "proof_tests", "require_proof_tests"}
ALLOWED_INTEGRITY = {"deleted_tests", "new_skips", "assertion_weakening", "ci_changes", "discovery_reduction", "coverage_exclusion", "snapshot_overwrite", "mock_weakening", "api_contract_changes"}
ALLOWED_DEPENDENCIES = {"lockfile_changes", "dependency_expansion"}
ALLOWED_COVERAGE = {"minimum_delta", "coverage_exclusion"}
ALLOWED_NETWORK = {"mode", "domains"}
ALLOWED_RECEIPT = {"signature_required", "trusted_public_keys"}
ALLOWED_SECURITY = {"isolated_runner_required"}


def _unknown_keys(section: str, value: Any, allowed: set[str]) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"Policy section '{section}' must be a mapping")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"Unknown keys in policy section '{section}': {', '.join(unknown)}")


def _validate_action(value: Any, location: str) -> str:
    if value not in VALID_ACTIONS:
        raise ValueError(f"Invalid policy action at {location}: {value!r}; expected ignore, warning, review, or block")
    return str(value)


def _normalize_proof_mode(verification: dict[str, Any]) -> None:
    mode = verification.get("proof_tests")
    if mode is None and "require_proof_tests" in verification:
        legacy = verification["require_proof_tests"]
        if not isinstance(legacy, bool):
            raise ValueError("verification.require_proof_tests must be boolean")
        mode = "required" if legacy else "off"
    if isinstance(mode, bool):
        mode = "required" if mode else "off"
    if mode not in VALID_PROOF_MODES:
        raise ValueError(f"Invalid verification.proof_tests: {mode!r}; expected off, auto, or required")
    verification["proof_tests"] = mode
    verification.pop("require_proof_tests", None)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(policy: dict[str, Any]) -> dict[str, Any]:
    unknown_top = sorted(set(policy) - ALLOWED_TOP_LEVEL)
    if unknown_top:
        raise ValueError(f"Unknown top-level policy keys: {', '.join(unknown_top)}")
    if policy.get("version") != 1:
        raise ValueError("Policy version must be 1")
    verification = policy.get("verification", {})
    _unknown_keys("verification", verification, ALLOWED_VERIFICATION)
    _normalize_proof_mode(verification)
    for section, allowed in (("integrity", ALLOWED_INTEGRITY), ("dependencies", ALLOWED_DEPENDENCIES), ("coverage", ALLOWED_COVERAGE), ("network", ALLOWED_NETWORK), ("receipt", ALLOWED_RECEIPT), ("security", ALLOWED_SECURITY)):
        if section in policy:
            _unknown_keys(section, policy[section], allowed)
    for key, value in policy.get("integrity", {}).items():
        _validate_action(value, f"integrity.{key}")
    for key, value in policy.get("dependencies", {}).items():
        _validate_action(value, f"dependencies.{key}")
    if "coverage_exclusion" in policy.get("coverage", {}):
        _validate_action(policy["coverage"]["coverage_exclusion"], "coverage.coverage_exclusion")
    network_mode = policy.get("network", {}).get("mode", "deny")
    if network_mode not in VALID_NETWORK_MODES:
        raise ValueError(f"Invalid network.mode: {network_mode!r}; expected deny, install-only, or allow")
    return policy


def _normalized(policy: dict[str, Any]) -> dict[str, Any]:
    result = _merge({}, policy)
    result.setdefault("verification", {})
    return _validate(result)


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
    if not policy:
        return "auto"
    verification = policy.get("verification", {})
    if not isinstance(verification, dict) or verification.get("proof_tests") not in VALID_PROOF_MODES:
        raise ValueError("Invalid verification.proof_tests")
    return str(verification["proof_tests"])


def action_for(policy: dict[str, Any], rule_id: str) -> str:
    integrity = {
        "AP001": "deleted_tests", "AP002": "new_skips", "AP003": "new_skips", "AP004": "discovery_reduction", "AP005": "assertion_weakening", "AP006": "coverage_exclusion",
        "AP007": "snapshot_overwrite", "AP008": "mock_weakening", "AP101": "ci_changes", "AP102": "ci_changes", "AP103": "ci_changes", "AP104": "ci_changes", "AP401": "api_contract_changes",
    }
    dependency = {"AP301": "dependency_expansion", "AP302": "lockfile_changes"}
    if rule_id in dependency:
        return _validate_action(policy.get("dependencies", {}).get(dependency[rule_id], "review"), f"dependencies.{dependency[rule_id]}")
    if rule_id == "AP006":
        value = policy.get("coverage", {}).get("coverage_exclusion", policy.get("integrity", {}).get("coverage_exclusion", "review"))
        return _validate_action(value, "coverage.coverage_exclusion")
    if rule_id in integrity:
        return _validate_action(policy.get("integrity", {}).get(integrity[rule_id], "warning"), f"integrity.{integrity[rule_id]}")
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

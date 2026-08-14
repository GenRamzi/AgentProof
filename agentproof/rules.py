from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    default_severity: str
    description: str


RULES = {
    "AP001": Rule("AP001", "Test Deleted", "high", "A test appears to have been deleted."),
    "AP002": Rule("AP002", "Test Skip Added", "high", "A skip or expected-failure marker was introduced."),
    "AP003": Rule("AP003", "Focused Test Added", "high", "A focused-test marker may exclude the rest of the suite."),
    "AP004": Rule("AP004", "Test Discovery Reduced", "high", "Test discovery or filtering scope was reduced."),
    "AP005": Rule("AP005", "Assertion Weakened", "high", "An assertion became less strict according to the configured analyzer."),
    "AP006": Rule("AP006", "Coverage Exclusion Added", "medium", "Coverage exclusions or thresholds were weakened."),
    "AP007": Rule("AP007", "Snapshot Overwrite", "medium", "Snapshots may have been regenerated or overwritten."),
    "AP008": Rule("AP008", "Mock Weakening", "medium", "An integration behavior appears to have been replaced by a mock."),
    "AP101": Rule("AP101", "CI Job Removed", "high", "A CI job or test step appears to have been removed."),
    "AP102": Rule("AP102", "CI Trigger Narrowed", "high", "A CI trigger or path filter became narrower."),
    "AP103": Rule("AP103", "Test Command Reduced", "high", "The configured test command now covers a smaller scope."),
    "AP104": Rule("AP104", "CI Configuration Changed", "medium", "CI or test configuration changed and requires review."),
    "AP201": Rule("AP201", "Proof Test Inconclusive", "medium", "The proof test passes on both base and PR revisions."),
    "AP202": Rule("AP202", "Proof Test Failed", "high", "The proof test does not pass on the PR revision."),
    "AP203": Rule("AP203", "Regression Detected", "high", "The proof test passed on base and failed on the PR revision."),
    "AP204": Rule("AP204", "Proof Test Unreproducible", "high", "The proof test could not be executed reproducibly."),
    "AP205": Rule("AP205", "Environment Mismatch", "medium", "Base and PR runs used materially different environments."),
    "AP301": Rule("AP301", "Dependency Expansion", "medium", "Dependency graph expansion was detected."),
    "AP302": Rule("AP302", "Lockfile Drift", "medium", "A dependency lockfile changed and requires review."),
    "AP401": Rule("AP401", "API Contract Changed", "high", "A public behavior or API contract changed."),
    "AP501": Rule("AP501", "Receipt Invalid", "high", "The receipt digest or schema is invalid."),
    "AP502": Rule("AP502", "Environment Untrusted", "high", "The execution environment does not meet the selected policy."),
}


def rule(rule_id: str) -> Rule:
    return RULES[rule_id]

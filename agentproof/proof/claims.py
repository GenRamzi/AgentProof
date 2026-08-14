from __future__ import annotations


def normalize_claim(text: str) -> str:
    value = text.lower()
    if "test" in value and "pass" in value:
        return "tests_pass"
    if "regression" in value or "coverage" in value:
        return "regression_test_added"
    if "backward" in value or "compatible" in value:
        return "backwards_compatible"
    if "bug" in value and "fix" in value:
        return "bug_fixed"
    return "custom_claim"

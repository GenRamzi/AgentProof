from __future__ import annotations

import ast
import re
from pathlib import Path

from ...models import Finding


_OPERATOR_STRENGTH = {
    "Eq": 5,
    "NotEq": 4,
    "Lt": 3,
    "LtE": 2,
    "Gt": 3,
    "GtE": 2,
    "In": 2,
    "NotIn": 2,
    "Is": 4,
    "IsNot": 4,
}


def _python_assertions(source: str) -> dict[int, tuple[str, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    result: dict[int, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and node.test.ops:
            operator = type(node.test.ops[0]).__name__
            result[node.lineno] = (operator, ast.unparse(node.test))
    return result


def _js_assertions(source: str) -> list[tuple[str, str]]:
    return re.findall(r"(?:expect\(([^\n]+)\)\.(?:toBe|toEqual|toStrictEqual)|assert\s*\(([^\n]+)\))", source)


def detect_assertion_weakening(base_root: Path, head_root: Path, changed_files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative in changed_files:
        if not re.search(r"\.(py|js|jsx|ts|tsx)$", relative, re.IGNORECASE):
            continue
        base_path = base_root / relative
        head_path = head_root / relative
        if not head_path.is_file():
            continue
        base_source = base_path.read_text(encoding="utf-8", errors="replace") if base_path.is_file() else ""
        head_source = head_path.read_text(encoding="utf-8", errors="replace")
        if relative.lower().endswith(".py"):
            base_asserts = _python_assertions(base_source)
            head_asserts = _python_assertions(head_source)
            suspicious: list[str] = []
            for line, (head_op, head_expr) in head_asserts.items():
                matching = base_asserts.get(line)
                if not matching:
                    continue
                base_op, base_expr = matching
                if _OPERATOR_STRENGTH.get(head_op, 0) < _OPERATOR_STRENGTH.get(base_op, 0):
                    suspicious.append(f"line {line}: {base_expr} -> {head_expr}")
            if suspicious:
                findings.append(Finding("AP005", "high", "An assertion became less strict according to Python AST comparison.", files=[relative], evidence=suspicious))
        else:
            base_lines = [line.strip() for line in base_source.splitlines() if "expect(" in line or "assert(" in line]
            head_lines = [line.strip() for line in head_source.splitlines() if "expect(" in line or "assert(" in line]
            if len(head_lines) < len(base_lines):
                findings.append(Finding("AP005", "high", "Assertion coverage appears to have been reduced in JavaScript/TypeScript.", files=[relative], evidence=[f"{len(base_lines)} assertions -> {len(head_lines)} assertions"]))
    return findings

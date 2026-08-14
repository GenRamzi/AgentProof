from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...models import Finding


def _keys(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        result: set[str] = set()
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            result.add(name)
            result |= _keys(child, name)
        return result
    if isinstance(value, list) and value:
        return _keys(value[0], prefix + "[]" if prefix else "[]")
    return set()


def compare_json_contracts(base_path: Path, head_path: Path, relative: str) -> list[Finding]:
    try:
        base = json.loads(base_path.read_text(encoding="utf-8"))
        head = json.loads(head_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    before, after = _keys(base), _keys(head)
    removed, added = sorted(before - after), sorted(after - before)
    if not removed and not added:
        return []
    evidence = ([f"Removed: {key}" for key in removed[:20]] + [f"Added: {key}" for key in added[:20]])
    return [Finding("AP401", "high", "A JSON behavior contract changed between base and PR.", files=[relative], evidence=evidence)]

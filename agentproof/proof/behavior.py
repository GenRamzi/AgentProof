from __future__ import annotations

import json
from typing import Any


def json_behavior_diff(base: Any, head: Any) -> dict[str, list[str]]:
    def keys(value: Any, prefix: str = "") -> set[str]:
        if isinstance(value, dict):
            output: set[str] = set()
            for key, child in value.items():
                name = f"{prefix}.{key}" if prefix else str(key)
                output.add(name)
                output |= keys(child, name)
            return output
        if isinstance(value, list) and value:
            return keys(value[0], prefix + "[]" if prefix else "[]")
        return set()
    before, after = keys(base), keys(head)
    return {"removed": sorted(before - after), "added": sorted(after - before)}


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)

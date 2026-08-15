from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Adapter:
    name: str
    command: str
    file_markers: tuple[str, ...]
    passed_pattern: str
    failed_pattern: str

    def parse_counts(self, output: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for key, pattern in (("passed", self.passed_pattern), ("failed", self.failed_pattern)):
            try:
                match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            except re.error:
                continue
            if not match:
                continue
            try:
                counts[key] = int(match.group(1)) if match.lastindex else 1
            except (TypeError, ValueError, IndexError):
                counts[key] = 1
        return counts

    def parse_result(self, output: str, exit_code: int) -> dict[str, int]:
        counts = self.parse_counts(output)
        if not counts and exit_code == 0:
            counts["passed"] = 1
        elif not counts and exit_code != 0:
            counts["failed"] = 1
        return counts


ADAPTERS = [
    Adapter("pytest", "pytest -q", ("pyproject.toml", "pytest.ini", "tests"), r"(\d+) passed", r"(\d+) failed"),
    Adapter("jest", "npm test", ("jest.config.js", "package.json"), r"Tests:\s+(\d+) passed", r"Tests:\s+(\d+) failed"),
    Adapter("vitest", "npm test", ("vitest.config.ts", "package.json"), r"Tests\s+(\d+)\s+passed", r"Tests\s+(\d+)\s+failed"),
    Adapter("node-test", "node --test", ("package.json",), r"(\d+) passing", r"(\d+) failing"),
    Adapter("cargo", "cargo test", ("Cargo.toml",), r"(\d+) passed", r"(\d+) failed"),
    Adapter("go", "go test ./...", ("go.mod",), r"\bok\b", r"\bFAIL\b"),
]


def adapter_for(command: str, cwd: Path | None = None) -> Adapter | None:
    lowered = command.lower()
    if "pytest" in lowered:
        return ADAPTERS[0]
    if "vitest" in lowered:
        return ADAPTERS[2]
    if "jest" in lowered:
        return ADAPTERS[1]
    if "node --test" in lowered:
        return ADAPTERS[3]
    if "cargo test" in lowered:
        return ADAPTERS[4]
    if "go test" in lowered:
        return ADAPTERS[5]
    if cwd is not None and (cwd / "package.json").is_file() and lowered in {"npm test", "npm run test"}:
        try:
            scripts = json.loads((cwd / "package.json").read_text(encoding="utf-8")).get("scripts", {})
            test_script = str(scripts.get("test", "")).lower()
            if "vitest" in test_script:
                return ADAPTERS[2]
            if "jest" in test_script:
                return ADAPTERS[1]
            if "node --test" in test_script:
                return ADAPTERS[3]
        except (OSError, json.JSONDecodeError):
            pass
    return None

from __future__ import annotations

import re
from dataclasses import dataclass


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
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                counts[key] = int(match.group(1))
        return counts


ADAPTERS = [
    Adapter("pytest", "pytest -q", ("pyproject.toml", "pytest.ini", "tests"), r"(\d+) passed", r"(\d+) failed"),
    Adapter("jest", "npm test", ("jest.config.js", "package.json"), r"Tests:\s+(\d+) passed", r"Tests:\s+(\d+) failed"),
    Adapter("vitest", "npm test", ("vitest.config.ts", "package.json"), r"(\d+) passed", r"(\d+) failed"),
    Adapter("node-test", "npm test", ("package.json",), r"(\d+) passing", r"(\d+) failing"),
    Adapter("cargo", "cargo test", ("Cargo.toml",), r"(\d+) passed", r"(\d+) failed"),
    Adapter("go", "go test ./...", ("go.mod",), r"ok", r"FAIL"),
]

from pathlib import Path

from agentproof.adapters.registry import adapter_for
from agentproof.engine.executor import _test_counts


def test_real_output_fixtures_are_parsed_without_crashing(tmp_path: Path):
    cases = [
        ("pytest -q", "================ 3 passed, 1 skipped in 0.10s ================", 0, {"passed": 3}),
        ("npm test", "Tests:       4 passed, 1 failed, 5 total", 1, {"passed": 4, "failed": 1}),
        ("npx vitest run", " Test Files  2 passed (2)\n Tests  7 passed (7)", 0, {"passed": 7}),
        ("node --test", "ℹ tests 3\nℹ pass 3\nℹ fail 0", 0, {"passed": 1}),
        ("cargo test", "test result: ok. 5 passed; 0 failed", 0, {"passed": 5, "failed": 0}),
        ("go test ./...", "ok   example.com/demo/pkg  0.012s", 0, {"passed": 1}),
        ("go test ./...", "FAIL\texample.com/demo/pkg\t0.012s", 1, {"failed": 1}),
    ]
    for command, output, exit_code, expected in cases:
        assert _test_counts(output, command, tmp_path, exit_code) == expected


def test_npm_test_selects_script_specific_adapter(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts": {"test": "vitest run"}}', encoding="utf-8")
    adapter = adapter_for("npm test", tmp_path)
    assert adapter is not None
    assert adapter.name == "vitest"


def test_unknown_output_returns_safe_counts(tmp_path: Path):
    assert _test_counts("unrecognized output", "unknown-command", tmp_path, 2) == {}

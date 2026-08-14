from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from agentproof.checks.ci.github_actions import detect_ci_integrity
from agentproof.checks.common import diff_by_file
from agentproof.checks.contracts.json_contract import compare_json_contracts
from agentproof.checks.dependencies.check import detect_dependency_integrity
from agentproof.checks.tests.discovery import (
    detect_deleted_tests,
    detect_discovery_reduction,
    detect_test_command_reduction,
)
from agentproof.checks.tests.focus import detect_focused_tests
from agentproof.checks.tests.mock import detect_mock_weakening
from agentproof.checks.tests.skips import detect_added_skips
from agentproof.checks.tests.snapshots import detect_coverage_and_snapshots
from agentproof.engine.verifier import verify_core
from agentproof.policy.evaluator import preset
from agentproof.receipt.verify import verify_receipt

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "fixtures" / "manifest.json"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def materialize(name: str, tmp_path: Path) -> tuple[Path, str, str]:
    source = ROOT / "fixtures" / name
    repo = tmp_path / name
    shutil.copytree(source / "base", repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof Fixture"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = git(repo, "rev-parse", "HEAD")
    for child in list(repo.iterdir()):
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(source / "head", repo, dirs_exist_ok=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "head"], cwd=repo, check=True)
    return repo, base, git(repo, "rev-parse", "HEAD")


def stable_findings(repo: Path, base: str, head: str):
    diff = diff_by_file(repo, base, head)
    findings = []
    for detector in (detect_added_skips, detect_focused_tests, detect_mock_weakening, detect_deleted_tests, detect_discovery_reduction, detect_test_command_reduction, detect_coverage_and_snapshots, detect_ci_integrity):
        findings.extend(detector(diff))
    files = [line for line in git(repo, "diff", "--name-only", f"{base}..{head}").splitlines() if line]
    findings.extend(detect_dependency_integrity(files, diff))
    for relative in files:
        contract_candidate = relative.endswith(("contract.json", ".schema.json")) or "/contracts/" in relative or "/schemas/" in relative
        if contract_candidate and (repo / relative).is_file():
            base_path = repo / ".base-snapshot" / relative
            base_path.parent.mkdir(parents=True, exist_ok=True)
            head_path = repo / relative
            subprocess.run(["git", "show", f"{base}:{relative}"], cwd=repo, text=True, stdout=base_path.open("w", encoding="utf-8"), check=False)
            if base_path.is_file():
                findings.extend(compare_json_contracts(base_path, head_path, relative))
    return findings


def test_all_declared_fixtures(tmp_path: Path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["fixtures"]:
        name = item["name"]
        if item.get("kind") == "receipt":
            valid, _, _ = verify_receipt(ROOT / "fixtures" / name / "head" / "receipt.json")
            assert not valid, name
            continue
        repo, base, head = materialize(name, tmp_path)
        if item.get("kind") == "policy":
            receipt = verify_core(repo, base, head, "python3 -m pytest -q", [], [], preset("enterprise"), timeout=60, auto_proof=False)
            assert "AP502" in {finding.rule for finding in receipt.findings}, name
            continue
        if item.get("proof"):
            command = "python3 -m pytest -q test_app.py::test_pending_is_ready" if name == "real-fix" else "python3 -m pytest -q test_app.py::test_claim"
            receipt = verify_core(repo, base, head, "python3 -m pytest -q", [command], [], preset("default"), timeout=60, auto_proof=False)
            assert receipt.proof_tests[0]["status"] == item["expected"], name
            continue
        if item.get("expected_rule") in {"AP005", "AP401"}:
            receipt = verify_core(repo, base, head, "python3 -m pytest -q", [], [], preset("default"), timeout=60, auto_proof=False)
            ids = {finding.rule for finding in receipt.findings}
        else:
            ids = {finding.rule for finding in stable_findings(repo, base, head)}
        assert item["expected_rule"] in ids, (name, item["expected_rule"], sorted(ids))

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time
from pathlib import Path

from ..adapters.registry import adapter_for
from .evidence import RunEvidence


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _test_counts(output: str, command: str = "", cwd: Path | None = None, exit_code: int = 0) -> dict[str, int]:
    adapter = adapter_for(command, cwd)
    if adapter is not None:
        return adapter.parse_result(output, exit_code)
    counts: dict[str, int] = {}
    patterns = {"passed": r"(\d+)\s+passed", "failed": r"(\d+)\s+failed", "skipped": r"(\d+)\s+skipped", "error": r"(\d+)\s+errors?"}
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            try:
                counts[key] = int(match.group(1))
            except (TypeError, ValueError, IndexError):
                counts[key] = 1
    return counts


def execute(command: str, cwd: Path, revision: str, commit_sha: str = "", environment_fingerprint: str = "", timeout: int = 600, dependency_lock_hash: str = "") -> RunEvidence:
    started = time.monotonic()
    env = {**os.environ, "CI": "true", "AGENTPROOF_NETWORK_MODE": os.environ.get("AGENTPROOF_NETWORK_MODE", "deny")}
    try:
        completed = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, timeout=timeout, env=env, check=False)
        exit_code = completed.returncode
        stdout, stderr = completed.stdout or "", completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        stderr += f"\nAgentProof: command timed out after {timeout}s."
    except OSError as exc:
        exit_code, stdout, stderr = 127, "", f"AgentProof: unable to execute command: {exc}"
    return RunEvidence(
        revision=revision,
        command=command,
        cwd=str(cwd),
        exit_code=exit_code,
        duration_seconds=round(time.monotonic() - started, 3),
        stdout_hash=_hash(stdout),
        stderr_hash=_hash(stderr),
        output_tail=(stdout + ("\n" + stderr if stderr else ""))[-12000:],
        test_counts=_test_counts(stdout + "\n" + stderr, command, cwd, exit_code),
        environment_fingerprint=environment_fingerprint,
        commit_sha=commit_sha,
        dependency_lock_hash=dependency_lock_hash,
    )

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

from .. import __version__

LOCKFILES = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "uv.lock",
    "Cargo.lock",
    "go.sum",
    "requirements.txt",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _version(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=5, check=False)
        return (result.stdout or result.stderr).strip().splitlines()[0][:200]
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def fingerprint(repo: Path, network_mode: str = "deny", runner_type: str = "local") -> dict[str, object]:
    locks = {name: sha256_file(repo / name) for name in LOCKFILES if (repo / name).is_file()}
    environment_allowlist = {
        key: os.environ[key]
        for key in ("CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_REPOSITORY", "GITHUB_SHA")
        if key in os.environ
    }
    data: dict[str, object] = {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": _version("python3 --version"),
        "node": _version("node --version"),
        "rust": _version("rustc --version"),
        "go": _version("go version"),
        "dependency_lock_hashes": locks,
        "environment_variables": environment_allowlist,
        "container_digest": os.environ.get("AGENTPROOF_CONTAINER_DIGEST", "unknown"),
        "network_mode": network_mode,
        "runner_type": runner_type,
        "agentproof_version": __version__,
    }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    data["fingerprint"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return data

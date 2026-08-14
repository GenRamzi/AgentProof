from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def run(repo: Path, *args: str) -> str:
    return subprocess.check_output(list(args), cwd=repo, text=True).strip()


def main() -> int:
    agentproof_root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="agentproof-demo-") as directory:
        repo = Path(directory)
        run(repo, "git", "init", "-q")
        run(repo, "git", "config", "user.email", "demo@example.com")
        run(repo, "git", "config", "user.name", "AgentProof Demo")
        (repo / "app.py").write_text("def ready(value):\n    return value == 'ready'\n")
        (repo / "test_app.py").write_text("from app import ready\n\ndef test_pending_is_ready():\n    assert ready('pending') is True\n")
        run(repo, "git", "add", ".")
        run(repo, "git", "commit", "-qm", "base")
        base = run(repo, "git", "rev-parse", "HEAD")
        (repo / "app.py").write_text("def ready(value):\n    return value in {'ready', 'pending'}\n")
        run(repo, "git", "add", "app.py")
        run(repo, "git", "commit", "-qm", "AI agent fix")
        head = run(repo, "git", "rev-parse", "HEAD")
        command = ["python", "-m", "agentproof", "verify", "--repo", str(repo), "--base", base, "--head", head, "--test-command", "python -m pytest -q", "--proof-test", "python -m pytest -q test_app.py::test_pending_is_ready"]
        completed = subprocess.run(command, cwd=agentproof_root, text=True, check=False)
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .models import TestRun


def run_command(command: str, cwd: Path, timeout: int = 600) -> TestRun:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env={**os.environ, "CI": "true"},
            check=False,
        )
        exit_code = completed.returncode
        output = completed.stdout or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        output = (exc.stdout or "") + f"\nAgentProof: command timed out after {timeout}s."
    except OSError as exc:
        exit_code = 127
        output = f"AgentProof: unable to execute command: {exc}"

    return TestRun(
        command=command,
        cwd=str(cwd),
        exit_code=exit_code,
        duration_seconds=round(time.monotonic() - started, 3),
        output_tail=output[-12000:],
    )

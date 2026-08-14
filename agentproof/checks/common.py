from __future__ import annotations

import re
from pathlib import Path


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    import subprocess
    result = subprocess.run(["git", "-c", "color.ui=false", "diff", "--name-only", f"{base}..{head}"], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def diff_by_file(repo: Path, base: str, head: str) -> dict[str, dict[str, list[tuple[int, str]]]]:
    import subprocess
    result = subprocess.run(["git", "-c", "color.ui=false", "diff", "--unified=0", f"{base}..{head}", "--"], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    output: dict[str, dict[str, list[tuple[int, str]]]] = {}
    current = ""
    new_line = 0
    for line in result.stdout.splitlines():
        header = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if header:
            current = header.group(2)
            output.setdefault(current, {"added": [], "removed": []})
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if hunk:
            new_line = int(hunk.group(1))
            continue
        if not current:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            output[current]["added"].append((new_line, line[1:]))
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            output[current]["removed"].append((new_line, line[1:]))
        elif line and not line.startswith("\\"):
            new_line += 1
    return output


def is_test_file(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|spec|__tests__)(/|$)|(^|/)(test[^/]*|[^/]*_test)\.(py|js|jsx|ts|tsx|go|rb|java)$|(_test\.|\.test\.|\.spec\.)", path, re.IGNORECASE))


def is_ci_file(path: str) -> bool:
    return bool(re.search(r"(^|/)(\.github/|\.gitlab-ci|jenkinsfile|tox\.ini|pytest\.ini|noxfile|pyproject\.toml|package\.json|jest\.config|vitest\.config|Makefile|Cargo\.toml|go\.mod)", path, re.IGNORECASE))

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def changed_line_coverage(coverage_json: Path, changed_files: list[str]) -> dict[str, Any]:
    if not coverage_json.is_file():
        return {"available": False, "reason": "coverage JSON not found"}
    try:
        data = json.loads(coverage_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "reason": str(exc)}
    covered = 0
    total = 0
    files = data.get("files", {})
    per_file: dict[str, dict[str, int]] = {}
    for relative in changed_files:
        entry = files.get(relative) or files.get(str(Path(relative)))
        if not entry:
            continue
        summary = entry.get("summary", {})
        file_total = int(summary.get("num_statements", 0))
        file_covered = int(summary.get("covered_lines", summary.get("num_statements", 0) - summary.get("missing_lines", 0)))
        total += file_total
        covered += file_covered
        per_file[relative] = {"covered": file_covered, "total": file_total}
    return {"available": True, "changed_lines_covered": covered, "changed_lines_total": total, "changed_lines_percent": round((covered / total) * 100, 2) if total else None, "files": per_file}

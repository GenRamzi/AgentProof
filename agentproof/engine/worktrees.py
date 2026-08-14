from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class WorktreeManager:
    def __init__(self, repo: Path):
        self.repo = repo
        self.paths: list[Path] = []

    def create(self, ref: str, name: str) -> Path:
        path = self.repo / ".agentproof-worktrees" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=self.repo, text=True, capture_output=True, check=False)
        subprocess.run(["git", "worktree", "add", "--detach", str(path), ref], cwd=self.repo, text=True, capture_output=True, check=True)
        self.paths.append(path)
        return path

    def create_transplant(self, base_ref: str, head_ref: str, relative_test: str, name: str) -> Path:
        base_path = self.create(base_ref, name)
        head_path = self.repo / ".agentproof-worktrees" / f"{name}-source"
        subprocess.run(["git", "worktree", "remove", "--force", str(head_path)], cwd=self.repo, text=True, capture_output=True, check=False)
        subprocess.run(["git", "worktree", "add", "--detach", str(head_path), head_ref], cwd=self.repo, text=True, capture_output=True, check=True)
        self.paths.append(head_path)
        source = head_path / relative_test
        target = base_path / relative_test
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return base_path

    def cleanup(self) -> None:
        for path in reversed(self.paths):
            subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=self.repo, text=True, capture_output=True, check=False)
        self.paths.clear()
        root = self.repo / ".agentproof-worktrees"
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)

    def __enter__(self) -> "WorktreeManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

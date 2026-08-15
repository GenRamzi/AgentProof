from __future__ import annotations

import json
from pathlib import Path


class CommandDiscoveryError(RuntimeError):
    pass


def discover_test_commands(repo: Path) -> list[str]:
    commands: list[str] = []
    if (repo / "pyproject.toml").is_file() or (repo / "pytest.ini").is_file() or (repo / "tests").is_dir():
        commands.append("pytest -q")
    package = repo / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.append("npm test")
            for name in scripts:
                if name.startswith("test:"):
                    commands.append(f"npm run {name}")
        except (OSError, json.JSONDecodeError):
            pass
    if (repo / "Cargo.toml").is_file():
        commands.append("cargo test")
    if (repo / "go.mod").is_file():
        commands.append("go test ./...")
    return list(dict.fromkeys(commands))


def discover_setup_commands(repo: Path) -> list[str]:
    """Return deterministic dependency/setup commands for a clean worktree."""
    commands: list[str] = []
    if (repo / "package-lock.json").is_file():
        commands.append("npm ci")
    elif (repo / "pnpm-lock.yaml").is_file():
        commands.append("pnpm install --frozen-lockfile")
    elif (repo / "yarn.lock").is_file():
        commands.append("yarn install --immutable")
    elif (repo / "package.json").is_file():
        commands.append("npm install")

    if (repo / "uv.lock").is_file():
        commands.append("uv sync --frozen")
    elif (repo / "poetry.lock").is_file():
        commands.append("poetry install --no-interaction")
    elif (repo / "requirements-dev.txt").is_file():
        commands.append("python -m pip install -r requirements-dev.txt")
    elif (repo / "requirements.txt").is_file():
        commands.append("python -m pip install -r requirements.txt")
    elif (repo / "pyproject.toml").is_file():
        commands.append("python -m pip install -e .")

    if (repo / "Cargo.toml").is_file():
        commands.append("cargo fetch")
    if (repo / "go.mod").is_file():
        commands.append("go mod download")
    return list(dict.fromkeys(commands))


def discover_canonical_command(repo: Path, configured: str | None = None) -> str:
    if configured:
        return configured
    commands = discover_test_commands(repo)
    if not commands:
        raise CommandDiscoveryError("No canonical test command detected. Set test_command in agentproof.yml or use --test-command.")
    if len(commands) > 1:
        raise CommandDiscoveryError("Ambiguous test commands detected: " + ", ".join(commands) + ". Set canonical test_command in agentproof.yml.")
    return commands[0]


def discover_setup_command(repo: Path, configured: str | None = None) -> str | None:
    if configured:
        return configured
    commands = discover_setup_commands(repo)
    return " && ".join(commands) if commands else None

from pathlib import Path

from agentproof.cli import main


def test_invalid_policy_is_configuration_error(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AgentProof Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    policy = tmp_path / "invalid.yml"
    policy.write_text("version: 1\nverification:\n  proof_tests: requred\n", encoding="utf-8")
    assert main(["verify", "--repo", str(repo), "--base", sha, "--head", sha, "--test-command", "true", "--policy", str(policy), "--json", str(tmp_path / "receipt.json"), "--markdown", str(tmp_path / "report.md")]) == 2

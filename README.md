# AgentProof

**Independent verification for AI-generated software.**

> AI wrote the code. AgentProof proves it works.

AgentProof is a deterministic verification layer that runs before AI-generated code is merged. It does not replace a coding agent, a code reviewer, or GitHub's security scanners. Instead, it independently reproduces the claims made by a pull request and looks for evidence that tests or CI were weakened to obtain a green result.

## What the MVP does

The first implementation focuses on four capabilities. It checks out the base and pull-request revisions into separate Git worktrees and runs the configured test command independently on both. It compares optional proof-test commands using the required behavior `BASE fails -> PR passes`, which distinguishes real regression coverage from a test that was already green. It scans the diff for high-signal test-integrity changes such as skip markers, focused tests, test deletion, discovery filters, coverage exclusions, and CI changes. Finally, it emits a human-readable report and a hash-addressed JSON receipt.

| Capability | MVP behavior |
|---|---|
| Independent test execution | Runs the same command on base and PR worktrees. |
| Proof Tests | Classifies a command as `PROVEN`, `INCONCLUSIVE`, `NOT_FIXED`, or `REGRESSION`. |
| Test integrity | Detects suspicious additions and deleted tests using deterministic rules. |
| Receipt | Writes `agentproof-receipt.json` with evidence, environment, findings, and SHA-256 integrity digest. |
| CI integration | Includes a pull-request workflow under `.github/workflows/agentproof.yml`. |

## Installation

```bash
python -m pip install .
```

For development, install pytest in the environment and run:

```bash
python -m pytest -q
```

## CLI usage

Run independent verification against two Git revisions:

```bash
agentproof verify \
  --repo . \
  --base origin/main \
  --head HEAD \
  --test-command "pytest -q" \
  --proof-test "pytest -q tests/test_race_condition.py" \
  --claim "All tests pass" \
  --claim "Added regression coverage"
```

The command writes `agentproof-receipt.json` and `agentproof-report.md`. It exits with status `0` only for `VERIFIED`; `INCONCLUSIVE` and `BLOCKED` are non-zero so a workflow cannot silently merge a result that needs review.

Validate the receipt digest:

```bash
agentproof verify-receipt agentproof-receipt.json
```

## Proof Tests

A proof test is stronger than a normal green test. AgentProof expects the test to fail on the base revision and pass on the pull-request revision:

```text
BASE: test_race_condition  FAIL
PR:   test_race_condition  PASS

Result: PROVEN
```

If the test passes on both revisions, AgentProof reports `INCONCLUSIVE`: the test does not independently demonstrate that the PR fixed the defect. If it fails on the PR, the result is `NOT_FIXED` or `REGRESSION` and the verification is blocked.

## Receipt shape

The receipt uses the versioned identifier `agentproof.receipt/v1`. It records the base and head revisions, commands, exit codes, durations, output tails, diff evidence, findings, proof-test classifications, environment metadata, and a SHA-256 digest over the canonical unsigned payload. The digest protects the receipt from accidental modification; a future release can add signed attestations and provenance without changing the core evidence model.

## GitHub Action

The included workflow runs on pull requests, checks out full history, installs AgentProof, verifies the base SHA against the head SHA, and uploads the receipt and Markdown report as artifacts. Set `--test-command` to the repository's canonical test command. Add one or more `--proof-test` arguments for claimed bug fixes.

For stronger isolation, run the workflow on a hardened or self-hosted runner with network egress restricted according to the repository's dependency-installation needs. The current CLI records the environment and marks network policy as caller-controlled; it does not claim to be a security sandbox by itself.

## Architecture

```text
Pull Request
     |
     v
AgentProof verifier
     |
     +-- clean base worktree --> test command
     +-- clean PR worktree   --> test command
     +-- diff audit           --> test/CI integrity findings
     +-- proof tests          --> base-vs-PR behavioral classification
     |
     v
Receipt + Markdown report + CI exit status
```

## Roadmap

The next engineering increments should add language-aware AST checks, coverage and mutation-testing evidence, API behavior snapshots, signed receipts, GitHub Check Run annotations, configurable policies, and a hardened execution backend. LLM reasoning should remain downstream of deterministic evidence rather than becoming the source of truth.

## License

Apache-2.0.

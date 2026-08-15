# AgentProof

**Independent verification for AI-generated software.**

> AI wrote the code. AgentProof proves it works.

AgentProof is not a coding agent, an AI code reviewer, or a security scanner. It is an independent verification layer for software changes produced by AI agents, human developers, or both. When a pull request claims that a bug was fixed, tests pass, or compatibility was preserved, AgentProof gathers deterministic evidence before merge.

## Why AgentProof exists

A green test result does not by itself prove that a new regression test catches the defect, that the full suite still runs, or that a CI configuration was not narrowed. AgentProof compares clean BASE and HEAD worktrees, reproduces the canonical test command, runs Proof Tests, audits test and CI integrity, records the environment, and emits a verifiable receipt.

> **Evidence first. AI reasoning second.**

## Demo in one minute

```bash
python -m pip install .
agentproof init
agentproof verify
```

A successful report looks like this:

```text
AgentProof
Independent verification

VERDICT: VERIFIED

✓ HEAD test command passes
✓ BASE and HEAD evidence recorded
✓ No deleted tests
✓ No new skips
✓ CI scope unchanged
✓ Proof test: BASE FAIL → HEAD PASS
```

A suspicious change is reported neutrally and can be blocked by policy:

```text
BLOCKED
AP004 Test Discovery Reduced
Previously: pytest tests/
Now:       pytest tests/unit/

The agent made the suite green by reducing the executed scope.
```

## Installation

```bash
python -m pip install .
python -m pytest -q
```

The Core is open source, requires no account, Cloud subscription, or API key, and can run locally or inside a read-only GitHub Actions pull-request workflow.

## One-command verification

With `agentproof.yml` present, the CLI discovers the canonical test command and Git base/head when possible:

```bash
agentproof verify
```

Explicit revisions and a Proof Test can be supplied:

```bash
agentproof verify \
  --repo . \
  --base origin/main \
  --head HEAD \
  --test-command "pytest -q" \
  --proof-test "pytest -q tests/test_race_condition.py" \
  --claim "All tests pass" \
  --claim "Added regression coverage" \
  --policy policies/strict.yml \
  --sarif agentproof.sarif
```

Additional commands are available for focused workflows:

```bash
agentproof init
agentproof proof
agentproof audit
agentproof receipt verify agentproof-receipt.json
agentproof explain AP005
agentproof doctor
```

## Proof Tests

A Proof Test is stronger than a normal green test. The strongest evidence is:

```text
BASE: FAIL
HEAD: PASS
=> PROVEN
```

AgentProof also distinguishes `INCONCLUSIVE`, `NOT_FIXED`, `REGRESSION`, `UNREPRODUCIBLE`, and `ENVIRONMENT_MISMATCH`. New conventional test files can be discovered and transplanted into BASE so a test added by a PR is evaluated against the old implementation.

## Integrity checks

Every finding has a stable rule ID for policies, CI, SARIF, and annotations.

| Rule family | Examples |
|---|---|
| Test integrity | `AP001` deleted tests, `AP002` new skips, `AP003` focused tests, `AP004` discovery reduced, `AP005` assertion weakened, `AP006` coverage exclusion, `AP007` snapshot overwrite. |
| CI integrity | `AP101` job removed, `AP102` trigger narrowed, `AP103` test command reduced, `AP104` CI changed. |
| Proof integrity | `AP201` inconclusive, `AP202` proof failed, `AP203` regression, `AP204` unreproducible, `AP205` environment mismatch. |
| Supply chain and contracts | `AP301` dependency expansion, `AP302` lockfile drift, `AP401` JSON contract changed. |
| Receipt and environment | `AP501` invalid receipt, `AP502` untrusted environment. |

Python assertions use AST-aware comparison in the first implementation. JavaScript and TypeScript are supported conservatively, with additional language adapters planned for Go, Rust, and Java.

## Policies

The repository ships `policies/default.yml`, `policies/strict.yml`, and `policies/enterprise.yml`. A policy controls required tests, Proof Tests, finding actions, dependency review, network mode, isolated-runner expectations, and signature requirements.

```yaml
version: 1
verification:
  require_tests: true
  require_proof_tests: true
integrity:
  deleted_tests: block
  new_skips: block
  assertion_weakening: block
  ci_changes: block
network:
  mode: deny
receipt:
  signature_required: true
```

The process records `deny`, `install-only`, or `allow` network mode in the environment fingerprint. A YAML field cannot create a firewall; production deployments must enforce the selected mode outside the test process.

## Receipt v1

Receipts use the stable identifier `agentproof.receipt/v1` and contain the repository subject, base/head SHAs, verdict, claims, Proof Tests, test runs, integrity findings, environment fingerprint, policy, evidence graph, and a canonical SHA-256 digest.

```bash
agentproof receipt verify agentproof-receipt.json
```

SHA-256 is the v0.1/v0.2 integrity mechanism. The data model leaves room for Ed25519, DSSE, in-toto, and Sigstore wrapping without inventing a private attestation format. A digest proves that the receipt content was not accidentally modified; it is not an identity signature.

## GitHub Action

Use the reusable action from a pull-request workflow:

```yaml
name: AgentProof
on:
  pull_request:
    types: [opened, synchronize, reopened]
permissions:
  contents: read
  pull-requests: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5
        with:
          fetch-depth: 0
      # Release-candidate example; pin to v0.2.0 or a full SHA after stable release.
      - uses: GenRamzi/AgentProof@v0.2.0rc2
        with:
          setup-command: python -m pip install -e ".[dev]"
          test-command: pytest -q
          policy: policies/strict.yml
```

The included workflow uses the unprivileged `pull_request` event. The current release-candidate reference is `GenRamzi/AgentProof@v0.2.0rc2`; after stable release, pin `GenRamzi/AgentProof@v0.2.0` or a full commit SHA and do not depend on a moving default branch.

It does not use `pull_request_target` to execute untrusted code, does not pass secrets to the PR, produces Markdown, JSON, and SARIF artifacts, and is explicit that the default CLI is not a security sandbox. `setup-command` runs independently in BASE and HEAD worktrees; setup failures are recorded as unreproducible evidence rather than misreported as test failures.

## Live demo

The public [agentproof-demo repository](https://github.com/GenRamzi/agentproof-demo) contains real pull-request scenarios for a genuine fix, deleted tests (AP001), skipped tests (AP002), narrowed CI, and fake regression tests. Its workflow uses the published `v0.2.0rc2` Action and preserves the resulting Receipt, Markdown, and SARIF artifacts.

## Current stable-release blocker

The `agentproof` distribution name is already occupied on PyPI by an unrelated project. AgentProof therefore remains in the release-candidate channel until a distinct distribution and product identity are selected and checked across PyPI, GitHub, and other public identities. Do not install an eventual stable release with `pip install agentproof` until that decision is complete.

## Architecture

```text
AI agent or human author
          |
       GitHub PR
          |
 AgentProof Core / Action
          |
   +------+-------+--------+
   |              |        |
Reproduce     Proof     Integrity
Tests         Tests      Analysis
   +------+-------+--------+
          |
     Evidence Graph
          |
 Receipt + Report + SARIF
```

The future GitHub App will create an `AgentProof / Verification` Check Run and line annotations, but the privileged API process must remain separate from the worker that executes untrusted PR code. Cloud, billing, dashboards, and centralized history are intentionally deferred until adoption demonstrates the need.

## Repository map

The expanded source layout separates Core engine code, integrity checks, Proof Tests, adapters, policies, receipts, reporters, schemas, fixtures, documentation, and future GitHub App boundaries. See [`docs/architecture.md`](docs/architecture.md), [`docs/threat-model.md`](docs/threat-model.md), [`docs/proof-tests.md`](docs/proof-tests.md), [`docs/receipts.md`](docs/receipts.md), and [`docs/policies.md`](docs/policies.md).

## Roadmap

The immediate target is a production-quality OSS MVP: Core verifier, Proof Tests, test and CI tampering checks, stable receipt, policies, fixtures, GitHub Action, documentation, and demo. Later phases add changed-line coverage, richer ASTs, SARIF annotations, GitHub App Checks API integration, behavior contracts, targeted mutation proof, signed attestations, and eventually Cloud when real users request centralized capabilities.

## License

Apache-2.0. See [`LICENSE`](LICENSE) and [`SECURITY.md`](SECURITY.md).

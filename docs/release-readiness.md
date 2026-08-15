# Release Readiness

## Release-candidate channel

The repository main branch currently identifies itself as unpublished `0.2.0rc3.dev0`. The previously published `v0.2.0rc1` and `v0.2.0rc2` tags remain immutable historical release candidates; the release workflow rejects any tag that does not exactly match the package version.

## RC gates

Before publishing a final RC, run a clean install, compile check, ruff, mypy, Python 3.10–3.14 matrix, full tests, fixture harness, coverage threshold, installed-wheel smoke test, fresh sdist install, twine metadata validation, SBOM validation, receipt schema and digest verification, external Action-path E2E, SARIF generation, and `pip-audit`. Each real repository run must provide a `setup-command` or use automatic ecosystem setup discovery; BASE, HEAD, manual-proof, and transplanted-proof setup evidence must appear in `setup_runs`. The public demo remains on historical RC2 until a renamed RC is published.

The RC should be exercised in three to five real Python repositories and at least one JavaScript/TypeScript repository. Those runs should be recorded as anonymized compatibility evidence rather than presented as fabricated adoption. `proof_tests: auto` should require Proof Tests for new regression tests or explicit bug-fix claims, but not for documentation or ordinary dependency updates.

## Stable release gates

Stable release is blocked until a distinct package and product identity is selected and verified on PyPI, GitHub, and the relevant public identity surfaces. The current `agentproof` PyPI distribution belongs to an unrelated project, so the existing distribution name must not be used for `v0.2.0`.

After the RC is green, create the immutable `v0.2.0` tag and GitHub Release. The release workflow generates distributions, checksums, build provenance, and release notes. PyPI publication uses GitHub OIDC Trusted Publishing and requires the repository-to-PyPI trusted publisher configuration to exist before the tag is pushed.

Stable users should pin `GenRamzi/AgentProof@v0.2.0` or a full commit SHA. The default branch is for development and must not be the documented stable dependency.

## Branch protection

The `main` branch requires the CI matrix and `AgentProof / Verification` checks, blocks force-push and deletion, and requires resolved review threads. It is currently configured with zero required approvals and no Code Owner approval because the project has one maintainer; those requirements should be raised when a second trusted maintainer joins.

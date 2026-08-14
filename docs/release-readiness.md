# Release Readiness

## Release-candidate channel

The repository currently identifies itself as `0.2.0rc1`. This is the first release candidate; it is not yet the stable `0.2.0` release. The immutable tag must be `v0.2.0rc1`, and the release workflow rejects any tag that does not exactly match the package version.

## RC gates

Before publishing `v0.2.0rc1`, run a clean install, compile check, ruff, mypy, Python 3.10–3.13 matrix, full tests, fixture harness, coverage threshold, installed-wheel smoke test, receipt schema and digest verification, external Action-path E2E, SARIF generation, and `pip-audit`. The demo repository must then use `GenRamzi/AgentProof@v0.2.0rc1` and exercise the AP001/AP002 scenarios.

The RC should be exercised in three to five real Python repositories and at least one JavaScript/TypeScript repository. Those runs should be recorded as anonymized compatibility evidence rather than presented as fabricated adoption.

## Stable release gates

After the RC is green, create the immutable `v0.2.0` tag and GitHub Release. The release workflow generates distributions, checksums, build provenance, and release notes. PyPI publication uses GitHub OIDC Trusted Publishing and requires the repository-to-PyPI trusted publisher configuration to exist before the tag is pushed.

Stable users should pin `GenRamzi/AgentProof@v0.2.0` or a full commit SHA. The default branch is for development and must not be the documented stable dependency.

## Branch protection

The `main` branch should require the CI matrix and `AgentProof / Verification` checks, disallow direct pushes, and require review. These repository settings require appropriate GitHub administrator permissions and are intentionally not represented as a local code claim.

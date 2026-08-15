# Changelog

## [Unreleased] — Post-RC hardening

Moved main to unpublished `0.2.0rc3.dev0` so it cannot emit a different artifact under the already-published RC2 version. Added a formal `setup-command` phase for canonical, manual, and transplanted Proof Tests, with `setup_runs` evidence and AP204 unreproducible semantics. Added separate BASE/HEAD environment fingerprints and lock hashes with AP205 runtime-only mismatch semantics. Added strict `proof_tests: off|auto|required` policy validation, synchronized Receipt schemas, resilient ecosystem adapters, explicit MANIFEST.in contents, fresh sdist/twine gates, SPDX SBOM generation, Python 3.14 CI, and secure two-job SARIF publication with `persist-credentials: false`.

The stable release remains blocked until a distinct package and product identity is selected because the `agentproof` PyPI distribution is occupied by an unrelated project.

## [0.2.0rc2] — Release Candidate

Corrected `environment.agentproof_version` so RC receipts use the single package version source instead of a stale hard-coded stable value. Added regression coverage for version consistency. The previously published `v0.2.0rc1` tag remains immutable.

## [0.2.0rc1] — Release Candidate

The first v0.2 release candidate adds lossless Receipt round trips, schema/digest/signature verification, optional Ed25519 signing, AP204/AP205 proof statuses, shell-safe targeted filenames, deterministic parser fuzz coverage, 90%+ coverage enforcement, PEP 440 tag validation, immutable release Action pins, Dependabot, CODEOWNERS, main-branch ruleset protection, and the external `agentproof-demo` validation repository.

## [0.2.0.dev0] — Development

AgentProof now includes a modular Core architecture with execution evidence, environment fingerprints, worktree management, stable AP rule IDs, policy presets, automatic test-command discovery, transplanted Proof Tests, JSON behavior contracts, dependency integrity checks, SARIF output, stable receipt schemas, receipt verification hooks, a reusable GitHub Action, security documentation, fixtures, and a production-oriented roadmap.

The receipt remains hash-addressed with SHA-256 in this release. Ed25519, DSSE, in-toto, and Sigstore integration are intentionally exposed as extension points rather than represented as completed signing guarantees.

## [0.1.0]

Initial open-source MVP with independent base/PR test execution, manual Proof Tests, first-generation test-integrity checks, JSON receipts, Markdown reports, and a repository workflow.

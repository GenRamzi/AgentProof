# AgentProof Roadmap

## v0.1.x — Production-quality OSS MVP

The first release focuses on Core verification, independent test reproduction, Proof Tests, test and CI integrity, stable receipts, policies, fixtures, the reusable GitHub Action, documentation, and a demo. It intentionally does not include Cloud, billing, dashboards, or a privileged GitHub App.

## v0.2 — Evidence depth

Add automatic proof-test discovery, Python and JavaScript/TypeScript AST analysis, changed-line coverage, SARIF annotations, policy configuration, and richer reporters.

## v0.3 — GitHub App

Add a split-trust GitHub App with Checks API integration, automatic PR verification, rerun support, and branch-protection guidance. The untrusted worker must remain isolated from the privileged App process.

## v0.4 — Behavior and dependency contracts

Add OpenAPI and JSON schema compatibility, CLI output contracts, public-function contracts, database migration checks, and dependency-integrity analysis.

## v0.5 — Targeted mutation and signing

Add mutation proof limited to changed functions and branches, automatic proof-test transplantation, Ed25519 local signatures, DSSE/in-toto export, and optional Sigstore verification.

## v1.0 — Stable verification infrastructure

Stabilize the CLI, Action, GitHub App, receipt and policy specifications, multi-language adapters, signed verification, public documentation, and a production-grade security model.

## Cloud trigger

Cloud should follow adoption rather than precede it. Signals include real repositories using AgentProof, external contributors, repeated verification runs, and users requesting history, central policies, private-repository execution, or organizational audit retention.

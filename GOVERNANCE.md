# Governance

AgentProof is governed by maintainers who prioritize deterministic evidence, reproducibility, security, and a low false-positive rate. Stable rule IDs and receipt schemas require a documented migration path; they should not be renamed casually because external CI policies depend on them.

New rules require an explanation, legitimate and adversarial fixtures, policy semantics, and regression tests. Security-sensitive changes require a threat-model update. Releases should pass the full fixture corpus, unit/integration/e2e tests, package build, and workflow hygiene checks.

The GitHub App and Cloud are separate future layers. They must not weaken the Core's account-free operation or cause untrusted PR execution to occur in a privileged context.

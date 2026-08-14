# AgentProof Threat Model

## Assets

The assets are repository source, workflow tokens, repository secrets, dependency credentials, the integrity of verification results, and the merge decision derived from a verdict.

## Adversaries

A malicious or compromised pull request may attempt to exfiltrate secrets, alter the test command, hide tests, abuse snapshots or mocks, exploit the runner, forge a receipt, or cause a false green result. A compromised dependency or action may attempt similar behavior.

## Required controls

AgentProof workflows must use `pull_request`, not `pull_request_target`, for untrusted code execution. They must request read-only repository permissions, pass no secrets to the test process, use a fresh runner where possible, and enforce network restrictions outside the Python process. The open-source local CLI must state that it is not a sandbox.

The verifier records output hashes, environment fingerprints, commit SHAs, lockfile hashes, and policy mode. Receipts are canonicalized and SHA-256 addressed. Future signed receipts should use established Ed25519, DSSE, in-toto, and Sigstore mechanisms rather than a custom trust system.

## Residual risk

A local invocation can still run arbitrary code with the caller's privileges. A deterministic static detector can produce false positives or miss language-specific manipulation. Test output can be misleading when a framework's discovery semantics are unknown. AgentProof therefore reports neutral findings and preserves evidence rather than claiming perfect security.

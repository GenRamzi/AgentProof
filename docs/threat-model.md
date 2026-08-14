# AgentProof Threat Model

## Assets

The assets are repository source, workflow tokens, repository secrets, dependency credentials, the integrity of verification results, and the merge decision derived from a verdict.

## Adversaries

A malicious or compromised pull request may attempt to exfiltrate secrets, alter the test command, hide tests, abuse snapshots or mocks, exploit the runner, forge a receipt, or cause a false green result. A compromised dependency or action may attempt similar behavior.

## Required controls

AgentProof workflows must use `pull_request`, not `pull_request_target`, for untrusted code execution. They must request read-only repository permissions, pass no secrets to the test process, use a fresh runner where possible, and enforce network restrictions outside the Python process. The open-source local CLI must state that it is not a sandbox.

The verifier records output hashes, environment fingerprints, commit SHAs, lockfile hashes, and policy mode. Receipts are canonicalized and SHA-256 addressed. Future signed receipts should use established Ed25519, DSSE, in-toto, and Sigstore mechanisms rather than a custom trust system.

Automatic proof commands are generated only for discovered test filenames and quote those filenames with shell-aware escaping before execution. A user-configured test command is intentionally treated as caller-controlled configuration and is not rewritten by AgentProof; repositories running untrusted code must therefore use a disposable runner and least-privilege permissions. Adversarial tests cover spaces, shell variables, quotes, Unicode, traversal strings, and command separators in filenames.

## v0.2 protection boundary

Version 0.2 is an evidence and policy layer, not a sandbox. The local CLI and the composite GitHub Action execute repository commands with the permissions of their runner. Fresh-VM or container isolation, CPU and memory limits, filesystem destruction, and real network egress enforcement remain deployment responsibilities. The recorded `network_mode: deny` value is an attested policy declaration; it is not a firewall and must not be represented as one.

The Action uses the unprivileged `pull_request` event and does not pass repository secrets to the verification command. It uploads receipt, Markdown, and SARIF artifacts, and a blocked verdict intentionally returns a nonzero process status so the pull request check fails while preserving evidence. The default policy does not require a signature; Enterprise signature and isolated-runner requirements are policy gates, and Ed25519 signing is optional rather than a universal trust guarantee.

## Residual risk

A local invocation can still run arbitrary code with the caller's privileges. A deterministic static detector can produce false positives or miss language-specific manipulation. Test output can be misleading when a framework's discovery semantics are unknown. AgentProof therefore reports neutral findings and preserves evidence rather than claiming perfect security.

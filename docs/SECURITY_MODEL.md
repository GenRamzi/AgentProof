# AgentProof Security Model

AgentProof is a verifier that executes potentially untrusted code. The system's security claim is therefore intentionally narrow: deterministic evidence is recorded, but the local CLI is not itself a sandbox. Production deployments must provide isolation.

A secure runner starts from a fresh VM or container, has no previous filesystem, receives no secrets, exposes no Docker socket, applies CPU/memory/time limits, restricts network egress, uses a temporary token only when needed, and destroys the environment after the run. GitHub workflows must use `pull_request` for untrusted code and must not use `pull_request_target` to execute the checked-out PR.

The receipt records the runner type, network mode, container digest when available, environment allowlist, runtime versions, dependency lock hashes, and AgentProof version. If these controls are absent, the receipt should describe the environment honestly rather than claiming a secure sandbox.

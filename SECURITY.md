# Security Model

AgentProof executes code from a pull request and therefore treats every PR revision as untrusted input. The project never uses `pull_request_target` to execute PR code, never grants production credentials to the verification process, and never exposes repository secrets to the checked-out PR.

## Execution boundary

The open-source CLI is not a security sandbox. It records the environment and supports a requested network mode, but local callers remain responsible for providing an isolated runner. For stronger guarantees, use a fresh ephemeral VM or container with no Docker socket, no inherited secrets, resource limits, restricted egress, and destruction after the run.

The included GitHub workflow uses the read-only `pull_request` event, `contents: read`, and `pull-requests: read`. Any future GitHub App must separate the untrusted verification worker from the privileged Check Runs API process.

## Network modes

Policies support `deny`, `install-only`, and `allow` with an explicit domain list. The current runner records the selected mode and does not claim that a local firewall has been enforced. A production runner must enforce the policy outside the test process.

## Reporting vulnerabilities

Please do not disclose sensitive vulnerabilities in a public issue. Open a private GitHub security advisory for `GenRamzi/AgentProof`, or contact the maintainers through the repository security channel. Include a minimal reproduction, affected version or commit, impact, and a suggested mitigation when available.

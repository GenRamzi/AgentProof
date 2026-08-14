# AgentProof GitHub App boundary

This directory reserves the future v0.3 GitHub App integration. The App should receive and authenticate pull-request webhook events, enqueue verification jobs, validate signed or digest-verified receipts, and create `AgentProof / Verification` Check Runs with annotations.

The webhook/API process must never execute the checked-out PR. Execution belongs to a separate untrusted worker running on a fresh isolated environment. The worker receives no GitHub write token or repository secrets. This boundary is intentionally documentation-only until the Core and Action have real adoption.

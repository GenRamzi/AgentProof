# GitHub App Design

The GitHub App is a future v0.3 integration, not a requirement for AgentProof Core. Its purpose is to receive pull-request events, dispatch an isolated verification run, validate a receipt, and create an `AgentProof / Verification` Check Run with a concise summary and annotations.

The App must not execute the PR in the privileged webhook process. A webhook receiver should authenticate the event, enqueue a job, and give a separate untrusted worker only the repository revision and non-secret configuration. The worker returns a receipt; the privileged process validates the digest and creates the Check Run. Reruns should create a new receipt rather than mutating historical evidence.

Branch protection and rulesets can require the check by name. Line annotations should point to the changed test or workflow line when the finding has a reliable location. The terminal and Markdown reports remain useful for local and Action users even after the App exists.

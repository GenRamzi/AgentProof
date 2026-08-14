# AgentProof Architecture

AgentProof has three product layers. **AgentProof Core** is open source, account-free, API-key-free, and responsible for deterministic verification. **AgentProof Action** packages Core for pull-request workflows. **AgentProof GitHub App** is a future privileged integration that will create Check Runs and annotations without executing untrusted PR code in the privileged process. Cloud is deliberately deferred until adoption justifies centralized history and policy management.

```text
AI agent or human author
          |
       GitHub PR
          |
     AgentProof Action
          |
   +------+-------+--------+
   |              |        |
Reproduction  Proof     Integrity
   |           Tests      Checks
   +------+-------+--------+
          |
     Evidence Graph
          |
   Receipt + Report + SARIF
```

The source of truth is deterministic evidence: Git revisions, commands, exit codes, output hashes, test counts, dependency lock hashes, AST comparisons, configuration diffs, environment fingerprints, and behavior snapshots. LLM reasoning may explain evidence later, but it cannot replace the evidence-producing operations.

## Split trust

A future GitHub App must use one process for untrusted execution and another for GitHub API writes. The execution worker receives no repository secrets, no write token, no production credentials, and no Docker socket. The App process receives signed results and creates Check Runs only after validating receipt integrity.

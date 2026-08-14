# AgentProof Demo Repository Scenario

The demo tells the product story in seconds:

1. An AI agent claims: `Fixed login race condition. Added regression tests. All tests pass.`
2. GitHub's ordinary CI is green.
3. The PR changed `pytest tests/` to `pytest tests/unit/`.
4. AgentProof compares the diff and reports `AP004 Test Discovery Reduced`.
5. A strict policy changes the result to `BLOCKED` and preserves the exact before/after command as evidence.

Run the demonstration in a temporary Git repository with:

```bash
agentproof audit --base BASE_SHA --head HEAD --policy policies/strict.yml
```

The demo is intentionally neutral. The output states what changed and why independent verification was reduced; it does not claim that the author had malicious intent.

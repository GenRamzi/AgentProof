# Proof Tests

A Proof Test must demonstrate a behavior change rather than merely pass. The strongest result is:

```text
BASE: FAIL
HEAD: PASS
=> PROVEN
```

If both revisions pass, the result is `INCONCLUSIVE`. If both fail, it is `NOT_FIXED`. If BASE passes and HEAD fails, it is `REGRESSION`. If the command cannot be run reliably, it is `UNREPRODUCIBLE`. If the base and head environments materially differ, it is `ENVIRONMENT_MISMATCH`.

## Automatic discovery

When a pull request adds a conventional test file under `tests`, `test`, `spec`, or `__tests__`, AgentProof can transplant that file into a BASE worktree and run the canonical suite. This detects a false regression test that only passes because the changed implementation is present. The transplanted result is recorded separately from the normal BASE and HEAD runs.

## Limits

Automatic discovery is conservative. It does not infer the bug's complete semantics, does not treat every new test as proof, and does not claim that a passing test proves backwards compatibility. A user can provide an explicit command with `--proof-test` when the test needs fixtures, environment setup, or a narrower invocation.

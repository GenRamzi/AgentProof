# Policies

Policies are YAML documents with `version: 1`. They control test and setup commands, conditional Proof Test requirements, integrity findings, the minimum coverage delta, dependency review, network mode, and receipt-signature requirements.

The repository ships three presets. **Default** warns on suspicious changes and uses `proof_tests: auto`. **Strict** blocks deleted tests, new skips, assertion weakening, CI changes, and lockfile changes while requiring Proof Tests only when a new regression test or explicit bug-fix claim is present. **Enterprise** inherits strict behavior, denies network access, requires an isolated runner, and requires a signed receipt.

```yaml
version: 1
verification:
  test_command: pytest -q
  setup_command: python -m pip install -e ".[test]"
  require_tests: true
  proof_tests: auto
integrity:
  deleted_tests: block
  new_skips: block
  assertion_weakening: block
  ci_changes: block
network:
  mode: deny
receipt:
  signature_required: true
```

Run a configured policy with `agentproof verify --policy agentproof.yml`. `setup_command`, when supplied, runs independently in BASE and HEAD worktrees before `test_command`; setup failures are recorded in `setup_runs` and classified as `INCONCLUSIVE` with AP204 rather than as test contradictions. Network mode is recorded and must be enforced by the runner or platform; the local process does not pretend that a YAML field can create a firewall.

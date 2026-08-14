# Policies

Policies are YAML documents with `version: 1`. They control whether tests and Proof Tests are required, how integrity findings are treated, the minimum coverage delta, dependency review, network mode, and receipt-signature requirements.

The repository ships three presets. **Default** warns on suspicious changes and allows a run to remain reviewable. **Strict** blocks deleted tests, new skips, assertion weakening, CI changes, and lockfile changes while requiring Proof Tests. **Enterprise** inherits strict behavior, denies network access, requires an isolated runner, and requires a signed receipt.

```yaml
version: 1
verification:
  require_tests: true
  require_proof_tests: true
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

Run a configured policy with `agentproof verify --policy agentproof.yml`. Network mode is recorded and must be enforced by the runner or platform; the local process does not pretend that a YAML field can create a firewall.

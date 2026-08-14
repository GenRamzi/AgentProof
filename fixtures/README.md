# AgentProof Fixture Corpus

Each fixture represents a base/head revision pair and an expected evidence outcome. The corpus is intended for unit, integration, adversarial, and release regression runs.

| Fixture | Scenario | Expected rule or proof outcome |
|---|---|---|
| `real-fix` | Base proof test fails and head passes | `PROVEN` |
| `fake-test` | Test passes on both revisions | `AP201 INCONCLUSIVE` |
| `test-deletion` | Existing test removed | `AP001` |
| `new-skip` | Skip marker introduced | `AP002` |
| `focused-test` | `.only()` or `fit()` introduced | `AP003` |
| `changed-filter` | Discovery scope reduced | `AP004` / `AP103` |
| `weakened-assertion` | Python comparison becomes weaker | `AP005` |
| `coverage-exclusion` | Coverage exclusion added | `AP006` |
| `snapshot-overwrite` | Snapshot update mode introduced | `AP007` |
| `ci-job-removal` | CI test job removed | `AP101` |
| `timeout-manipulation` | Timeout increased materially | regression rule coverage |
| `dependency-explosion` | Dependency graph expands | `AP301` / `AP302` |
| `api-break` | JSON contract key changes | `AP401` |

Fixtures are source examples rather than claims of malicious intent. Reports should state the observed change and its effect on independent verification.

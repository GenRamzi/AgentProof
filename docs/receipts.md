# Receipts

A Receipt v1 is a stable, machine-readable record of one verification attempt:

```json
{
  "schema": "agentproof.receipt/v1",
  "subject": {"repository": "owner/repo", "base_sha": "...", "head_sha": "..."},
  "verdict": "VERIFIED",
  "claims": [],
  "proof_tests": [],
  "test_runs": [],
  "integrity_findings": [],
  "environment": {},
  "policy": {},
  "digest": "sha256:..."
}
```

The digest is calculated over canonical JSON with the digest and signature fields omitted. `agentproof receipt verify` recomputes the digest and fails with AP501 semantics when it differs. This is an integrity check, not an identity signature.

The model leaves room for later Ed25519 local signatures and keyless OIDC/Sigstore verification. It can also be exported into an in-toto or DSSE attestation without conflating behavioral verification evidence with GitHub artifact provenance.

## Claim statuses

`PROVEN` means the evidence directly satisfies the claim. `SUPPORTED` means the evidence supports the claim but does not fully prove it. `UNPROVEN` means no sufficient evidence was collected. `CONTRADICTED` means independent evidence conflicts with the claim. `NOT_APPLICABLE` means the claim was not relevant to the run.

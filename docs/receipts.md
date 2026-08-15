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

`setup_runs` records dependency/setup execution independently from `test_runs`. The `environment` object contains separate `base` and `head` fingerprints plus a comparison summary; dependency-lock hashes are retained as evidence but are not themselves an AP205 runtime mismatch.

The optional Ed25519 signature is a self-contained integrity signature: the Receipt can prove that its payload and signature match, but a public key embedded in the Receipt does not establish trusted signer identity. Trusted enterprise attestation requires an external trusted-key configuration or a future keyless OIDC/Sigstore, in-toto, or DSSE integration. The model can export into those formats without conflating behavioral verification evidence with GitHub artifact provenance.

## Claim statuses

`PROVEN` means the evidence directly satisfies the claim. `SUPPORTED` means the evidence supports the claim but does not fully prove it. `UNPROVEN` means no sufficient evidence was collected. `CONTRADICTED` means independent evidence conflicts with the claim. `NOT_APPLICABLE` means the claim was not relevant to the run.

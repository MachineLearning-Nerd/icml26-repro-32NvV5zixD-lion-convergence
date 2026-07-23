# Claim 5 — unbiased sign compression

**Verdict: VERIFIED.** Both learning-rate choices were tested against their complete two-term rates:

- `O(d^(1/2)T^(-1/2) + dn^(-1/2))`
- `O(n^(1/2)T^(-1) + dn^(-1/2))`

Across dimensions `16,64`, nodes `3,9`, horizons `256,1024,4096`, both schedules, and 12 deterministic seed lanes, the observed stationarity measure divided by the applicable complete rate stayed in `0.149…1.015`.

Evidence: `evidence/claim_5/`.

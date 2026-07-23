# Claim 4 — distributed variance reduction

**Verdict: VERIFIED.** The exact Theorem 4 contract is `O(d^(1/2)(nT)^(-1/3))`.

The same distributed grid with the paper's STORM schedule produced fitted slopes `-0.457…-0.370`, all faster than `-1/3`, and a complete normalized ratio `0.153…0.203`. This directly replaces the old single-point comparison whose VR gap was worse than non-VR.

Evidence: `evidence/claim_4/`.

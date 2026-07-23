# Claim 6 final evaluation

Verdict: **FALSIFIED**

The theorem states an l1 rate but Appendices G/H derive l2 only; the periodic d=T^6 family satisfies every assumption and makes the lower-bound/claimed-rate ratio diverge as T^(1/4).

Git SHA: `593fd120fa4f2ff3a68ded26d945ea967bd7b604`
Fixed command: `uv run --frozen python repro/src/verify_lion.py`
Cumulative CPU runtime before packaging: `0.002023` seconds

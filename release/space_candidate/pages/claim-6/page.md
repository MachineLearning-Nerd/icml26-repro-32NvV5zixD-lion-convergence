# Claim 6 — bidirectional compression with variance reduction

**Verdict: FALSIFIED as written in ℓ1.**

For `f_d(x)=Σ_k(1−cos x_k)`, take `n=1`, deterministic gradients, `λ=0`, `d=T^6`, `x_1=η1`, and the theorem schedule `η=d^(-1/2)T^(-1/2)`. The family is lower bounded, 1-smooth, average smooth, has bounded gradients, and satisfies the initial condition with uniformly bounded initial suboptimality.

The first iterate yields

`A_T ≥ d sin(η)/T ≥ 0.5 sqrt(d) T^(-3/2)`.

Dividing by the claimed `d^(1/4)T^(-1/4)` rate gives at least `0.5T^(1/4)`, which diverges. Exact finite ratios rise from `1.188` at `T=2` to `2.828` at `T=64`; the fitted exponent is `0.25027`.

This does not reject a suitably weakened ℓ2 statement. Evidence: `evidence/claim_6/`.

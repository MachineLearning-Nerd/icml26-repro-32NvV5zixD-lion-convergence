# Source audit — Claim 5

- Primary source: `https://export.arxiv.org/e-print/2508.12327` (`arXiv:2508.12327v1`)
- Source SHA-256: `cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688`
- LaTeX anchor: `thm5`
- Displayed theorem: `5`
- Quantity: `T^-1 sum_t E[||grad f(x_t)||_1]`
- Exact assumptions: ass:1+, ass:3+, ass0+, bg1
- Exact schedule: `{"beta1": "beta2^2 <= beta1 <= sqrt(beta2)", "beta2": "1/2", "eta_a": "O(T^(-1/2)d^(-1/2))", "eta_b": "O(n^(-1/2))", "lambda": "<= 1/(2 eta T)"}`
- Quantifier reading: For bounded per-node stochastic gradients and independent unbiased upload signs, either learning-rate choice gives its displayed expected l1 bound.

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.

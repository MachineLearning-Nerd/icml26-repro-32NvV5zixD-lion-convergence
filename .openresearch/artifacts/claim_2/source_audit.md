# Source audit — Claim 2

- Primary source: `https://export.arxiv.org/e-print/2508.12327` (`arXiv:2508.12327v1`)
- Source SHA-256: `cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688`
- LaTeX anchor: `thm1+++`
- Displayed theorem: `2`
- Quantity: `T^-1 sum_t E[||grad f(x_t)||_1]`
- Exact assumptions: ass:2, ass:3, ass0
- Exact schedule: `{"B0": "O(T^(1/3))", "beta1": "beta2 <= beta1 <= sqrt(beta2)", "beta2": "O(T^(-2/3))", "eta": "O(d^(-1/2) T^(-2/3))", "initial": "||x1||_infinity <= eta", "lambda": "<= 1/(2 eta T)"}`
- Quantifier reading: For every average-smooth stochastic objective satisfying the listed assumptions and every compliant parameter choice, the expected l1 time-average has the displayed rate.

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.

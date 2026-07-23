# Source audit — Claim 4

- Primary source: `https://export.arxiv.org/e-print/2508.12327` (`arXiv:2508.12327v1`)
- Source SHA-256: `cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688`
- LaTeX anchor: `thm4`
- Displayed theorem: `4`
- Quantity: `T^-1 sum_t E[||grad f(x_t)||_1]`
- Exact assumptions: ass:2+, ass:3+, ass0+
- Exact schedule: `{"B0": "O(n^(-2/3) T^(1/3))", "beta1": "beta1 <= sqrt(beta2)", "beta2": "O(n^(1/3) T^(-2/3))", "domain": "T >= n^2", "eta": "O(n^(1/3) d^(-1/2) T^(-2/3))", "initial": "||x1||_infinity <= eta", "lambda": "<= 1/(2 eta T)"}`
- Quantifier reading: For n independent heterogeneous workers satisfying per-node average smoothness, the expected l1 time-average has the displayed joint n,T rate.

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.

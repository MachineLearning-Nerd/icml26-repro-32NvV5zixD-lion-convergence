# Source audit — Claim 1

- Primary source: `https://export.arxiv.org/e-print/2508.12327` (`arXiv:2508.12327v1`)
- Source SHA-256: `cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688`
- LaTeX anchor: `thm1++`
- Displayed theorem: `1`
- Quantity: `T^-1 sum_t E[||grad f(x_t)||_1]`
- Exact assumptions: ass:1, ass:3, ass0
- Exact schedule: `{"beta1": "beta2^2 <= beta1 <= sqrt(beta2)", "beta2": "O(T^(-1/2))", "eta": "O(d^(-1/2) T^(-3/4))", "initial": "||x1||_infinity <= eta", "lambda": "<= 1/(2 eta T)"}`
- Quantifier reading: For every stochastic objective satisfying the listed assumptions and every compliant parameter choice, the displayed expected time-average is bounded up to constants independent of d and T.

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.

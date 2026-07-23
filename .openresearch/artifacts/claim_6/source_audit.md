# Source audit — Claim 6

- Primary source: `https://export.arxiv.org/e-print/2508.12327` (`arXiv:2508.12327v1`)
- Source SHA-256: `cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688`
- LaTeX anchor: `thm8`
- Displayed theorem: `7`
- Quantity: `T^-1 sum_t E[||grad f(x_t)||_1]`
- Exact assumptions: ass:2+, ass:3+, ass0+, bg1
- Exact schedule: `{"beta1": "beta1 <= sqrt(beta2)", "beta2": "O(T^(-1/2))", "eta": "O(d^(-1/2)T^(-1/2))", "initial": "||x1||_infinity <= eta", "lambda": "<= min(sqrt(L)/(T sqrt(eta G)), 1/(2 eta T))"}`
- Quantifier reading: The displayed l1 rate is asserted uniformly over dimensions and horizons for every compliant average-smooth bounded-gradient problem.

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.

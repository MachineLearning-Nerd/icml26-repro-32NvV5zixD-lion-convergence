# Claims


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_f70a3bd15eb5", "created_at": "2026-07-21T15:14:43+00:00", "title": "Claims to reproduce"}
-->
## Claims to reproduce

1. Theorem 1 proves centralized Lion achieves a convergence rate of O(d^{1/2} T^{-1/4}) under standard smoothness, without requiring the coerciveness assumption used in prior analyses (Theorem 1).
2. Theorem 2 shows that a variance-reduced Lion variant using STORM-based gradient estimators improves the rate to O(d^{1/2} T^{-1/3}) under an average smoothness assumption (Theorem 2).
3. Theorem 3 establishes that distributed Lion across n heterogeneous nodes matches the centralized rate, converging as O(d^{1/2} (nT)^{-1/4}) (Theorem 3).
4. Theorem 4 shows that adding variance reduction to distributed Lion improves the distributed rate to O(d^{1/2} (nT)^{-1/3}) (Theorem 4).
5. Theorem 5 gives a communication-efficient Lion variant with unbiased sign compression achieving either O(d^{1/2} T^{-1/2} + d n^{-1/2}) or O(n^{1/2} T^{-1} + d n^{-1/2}) depending on the learning-rate choice (Theorem 5).
6. Theorem 7 shows that combining bidirectional unbiased sign compression with variance reduction attains a communication-efficient rate of O(d^{1/4} T^{-1/4}), improving over the non-variance-reduced Theorem 6 rate (Theorem 7, Theorem 6).

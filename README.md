# Lion convergence claims — rigorous reproduction

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/blob/master/notebooks/lion_claims.py)

This repository reproduces all six scored claims from [Convergence Analysis of the Lion Optimizer in Centralized and Distributed Settings](https://arxiv.org/abs/2508.12327) (OpenReview `32NvV5zixD`). The previous judged revision earned **6/12** because it only checked convergence on a noisy `d=10` quadratic. The new evidence audits the exact theorem contracts, measures every stated assumption, fits the claimed exponents over dimensions, horizons, nodes, schedules, and deterministic seeds, and runs independent and deliberately corrupted negative controls.

**Assessment, not a judge result:** Claims 1–5 are `VERIFIED`; Claim 6 is `FALSIFIED` as written by an assumption-satisfying counterexample to its stated ℓ1 rate. This supports a conservative **10–12/12 forecast** and a best-supported possible **12/12 forecast**. The live score remains **6/12** until a judge evaluates a future approved Space revision.

The paper predicts horizon exponents `-1/4`, `-1/3`, `-1/4`, and `-1/3` for Claims 1–4. Across the tested theorem-faithful grids, observed fitted slopes were `[-0.288,-0.283]`, `[-0.386,-0.379]`, `[-0.265,-0.254]`, and `[-0.457,-0.370]`, respectively. Claim 5's complete two-term normalized ratio stayed in `[0.149,1.015]`. Claim 6's counterexample ratio grew with fitted exponent `+0.25027`, matching the derived `T^(1/4)` divergence.

The agreed compute was one local Apple CPU (`8` logical CPUs); no GPU and no Hugging Face cpu-upgrade were used. The evidence is theorem-faithful synthetic and analytic evidence, not a deep-learning application benchmark.

- [Illustrated technical report](reports/lion-convergence-2026-07-23/report.md)
- [Self-contained marimo tutorial](notebooks/lion_claims.py)
- [Machine-readable final verdict](.openresearch/artifacts/final_verdict.json)
- [Per-claim evidence](.openresearch/artifacts/)

## Experiment log

The exact run command was fixed once and inherited unchanged:

| Branch / experiment | Purpose or change | Exact run command | Assessment / outcome | Compute |
| --- | --- | --- | --- | --- |
| [`orx/frozen-judged-d-10-baseline`](https://github.com/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/tree/orx/frozen-judged-d-10-baseline) | Freeze and reproduce the judged toy checks | `uv run --frozen python repro/src/verify_lion.py` | Reproduced the six `d=10` toy outputs; retained only as regression control | local CPU, 20s |
| [`orx/exact-theorem-contracts-and-proof-audit`](https://github.com/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/tree/orx/exact-theorem-contracts-and-proof-audit) | Exact source contracts and rate-substitution audit | `uv run --frozen python repro/src/verify_lion.py` | Claims 1–5 analytically supported; Claim 6 validly falsified | local CPU, 30s |
| [`orx/multi-axis-stochastic-rate-scaling`](https://github.com/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/tree/orx/multi-axis-stochastic-rate-scaling) | 1,776-row stochastic scaling study | `uv run --frozen python repro/src/verify_lion.py` | Claims 1–5 empirically supported with measured assumptions | local CPU, 2m48s |
| [`orx/cumulative-theorem-evidence-suite`](https://github.com/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/tree/orx/cumulative-theorem-evidence-suite) | Combine both routes and fail closed | `uv run --frozen python repro/src/verify_lion.py` | Claims 1–5 `VERIFIED`; Claim 6 `FALSIFIED` | local CPU, 40s |
| [`orx/durable-cumulative-evidence-pack`](https://github.com/MachineLearning-Nerd/icml26-repro-32NvV5zixD-lion-convergence/tree/orx/durable-cumulative-evidence-pack) | Commit and verify the log-emitted evidence pack | `uv run --frozen python repro/src/verify_lion.py` | 135 hashes and all 1,776 rows verified before full regeneration | local CPU, 1m00s |
| `master` | Public README, report, notebook, and release surface | Not run as an experiment (publication surface) | Presentation-only; evidence originates from the frozen experiment branches above | none |

## Reproduce

```bash
uv sync --frozen
uv run --frozen python repro/src/verify_lion.py
```

The verifier exits nonzero if a claim contract, assumption check, independent checker, negative control, evidence hash, or cumulative verdict fails. Python `3.12.11` and NumPy `2.3.1` are locked in `uv.lock`.

## Original repository note

Repro — Convergence Analysis of the Lion Optimizer. OpenReview `32NvV5zixD`. arXiv `2508.12327`. Six claims / 12 possible points.

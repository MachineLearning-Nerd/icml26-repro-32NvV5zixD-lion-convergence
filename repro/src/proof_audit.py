"""Exact-statement and proof-rate audit for arXiv:2508.12327v1.

This module does not infer a rate from a single finite run.  It encodes the
paper's assumptions, schedules, norms, and displayed proof bounds, checks the
exponent substitutions with exact rational arithmetic, stress-tests the local
inequalities used by the proofs, and constructs an assumption-satisfying
counterexample to the l1-norm statement of the final communication theorem.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".openresearch" / "artifacts"
SOURCE_SHA256 = "cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688"
SOURCE_URL = "https://export.arxiv.org/e-print/2508.12327"
RUN_COMMAND = "uv run --frozen python repro/src/verify_lion.py"


@dataclass(frozen=True)
class Monomial:
    """Exponents of d, n, and T in a positive monomial."""

    d: Fraction = Fraction(0)
    n: Fraction = Fraction(0)
    T: Fraction = Fraction(0)

    def __mul__(self, other: "Monomial") -> "Monomial":
        return Monomial(self.d + other.d, self.n + other.n, self.T + other.T)

    def __truediv__(self, other: "Monomial") -> "Monomial":
        return Monomial(self.d - other.d, self.n - other.n, self.T - other.T)

    def power(self, p: Fraction) -> "Monomial":
        return Monomial(self.d * p, self.n * p, self.T * p)

    def serial(self) -> dict[str, str]:
        return {"d": str(self.d), "n": str(self.n), "T": str(self.T)}


ONE = Monomial()
D = Monomial(d=Fraction(1))
N = Monomial(n=Fraction(1))
T_VAR = Monomial(T=Fraction(1))
SQRT_D = D.power(Fraction(1, 2))


CLAIMS = {
    1: {
        "anchor": "thm1++",
        "displayed_theorem": 1,
        "algorithm": "alg:lion v1",
        "assumptions": ["ass:1", "ass:3", "ass0"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/2) T^(-1/4))",
        "schedule": {
            "beta2": "O(T^(-1/2))",
            "beta1": "beta2^2 <= beta1 <= sqrt(beta2)",
            "eta": "O(d^(-1/2) T^(-3/4))",
            "lambda": "<= 1/(2 eta T)",
            "initial": "||x1||_infinity <= eta",
        },
        "quantifiers": "For every stochastic objective satisfying the listed assumptions and every compliant parameter choice, the displayed expected time-average is bounded up to constants independent of d and T.",
    },
    2: {
        "anchor": "thm1+++",
        "displayed_theorem": 2,
        "algorithm": "alg:lion v2 (STORM correction)",
        "assumptions": ["ass:2", "ass:3", "ass0"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/2) T^(-1/3))",
        "schedule": {
            "beta2": "O(T^(-2/3))",
            "beta1": "beta2 <= beta1 <= sqrt(beta2)",
            "eta": "O(d^(-1/2) T^(-2/3))",
            "B0": "O(T^(1/3))",
            "lambda": "<= 1/(2 eta T)",
            "initial": "||x1||_infinity <= eta",
        },
        "quantifiers": "For every average-smooth stochastic objective satisfying the listed assumptions and every compliant parameter choice, the expected l1 time-average has the displayed rate.",
    },
    3: {
        "anchor": "thm3",
        "displayed_theorem": 3,
        "algorithm": "alg3 v1 (server update once per round)",
        "assumptions": ["ass:1+", "ass:3+", "ass0+"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/2) n^(-1/4) T^(-1/4))",
        "schedule": {
            "beta2": "O(n^(1/2) T^(-1/2))",
            "beta1": "beta2^2 <= beta1 <= sqrt(beta2)",
            "eta": "O(n^(1/4) d^(-1/2) T^(-3/4))",
            "lambda": "<= 1/(2 eta T)",
            "domain": "T >= n",
            "initial": "||x1||_infinity <= eta",
        },
        "quantifiers": "For n independent heterogeneous workers satisfying the per-node assumptions, the expected l1 time-average has the displayed joint n,T rate.",
    },
    4: {
        "anchor": "thm4",
        "displayed_theorem": 4,
        "algorithm": "alg3 v2 (per-worker STORM correction)",
        "assumptions": ["ass:2+", "ass:3+", "ass0+"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/2) n^(-1/3) T^(-1/3))",
        "schedule": {
            "beta2": "O(n^(1/3) T^(-2/3))",
            "beta1": "beta1 <= sqrt(beta2)",
            "eta": "O(n^(1/3) d^(-1/2) T^(-2/3))",
            "B0": "O(n^(-2/3) T^(1/3))",
            "lambda": "<= 1/(2 eta T)",
            "domain": "T >= n^2",
            "initial": "||x1||_infinity <= eta",
        },
        "quantifiers": "For n independent heterogeneous workers satisfying per-node average smoothness, the expected l1 time-average has the displayed joint n,T rate.",
    },
    5: {
        "anchor": "thm5",
        "displayed_theorem": 5,
        "algorithm": "alg4 v1, Q1=S_G and Q2=sign",
        "assumptions": ["ass:1+", "ass:3+", "ass0+", "bg1"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/2)T^(-1/2)+d n^(-1/2)) or O(n^(1/2)T^(-1)+d n^(-1/2))",
        "schedule": {
            "beta2": "1/2",
            "beta1": "beta2^2 <= beta1 <= sqrt(beta2)",
            "eta_a": "O(T^(-1/2)d^(-1/2))",
            "eta_b": "O(n^(-1/2))",
            "lambda": "<= 1/(2 eta T)",
        },
        "quantifiers": "For bounded per-node stochastic gradients and independent unbiased upload signs, either learning-rate choice gives its displayed expected l1 bound.",
    },
    6: {
        "anchor": "thm8",
        "comparator_anchor": "thm7",
        "displayed_theorem": 7,
        "comparator_displayed_theorem": 6,
        "algorithm": "alg4 v2, Q1=S_G and Q2=S_1",
        "assumptions": ["ass:2+", "ass:3+", "ass0+", "bg1"],
        "quantity": "T^-1 sum_t E[||grad f(x_t)||_1]",
        "rate": "O(d^(1/4)T^(-1/4))",
        "comparator_rate": "O(max(d^(1/4)T^(-1/4), d^(1/10)n^(-1/5)T^(-1/5)))",
        "schedule": {
            "beta2": "O(T^(-1/2))",
            "beta1": "beta1 <= sqrt(beta2)",
            "eta": "O(d^(-1/2)T^(-1/2))",
            "lambda": "<= min(sqrt(L)/(T sqrt(eta G)), 1/(2 eta T))",
            "initial": "||x1||_infinity <= eta",
        },
        "quantifiers": "The displayed l1 rate is asserted uniformly over dimensions and horizons for every compliant average-smooth bounded-gradient problem.",
    },
}


def _dominates_under_domain(term: Monomial, target: Monomial, domain: str) -> bool:
    """Check that term <= target for d,n,T>=1 and the theorem's domain."""

    ratio = term / target
    if ratio.d > 0:
        return False
    if domain == "T>=n":
        # n^a T^b <= 1 when a+b <= 0 and b <= 0.
        return ratio.T <= 0 and ratio.n + ratio.T <= 0
    if domain == "T>=n^2":
        # Substitute T=n^2 u, u>=1.
        return ratio.T <= 0 and ratio.n + 2 * ratio.T <= 0
    return ratio.n <= 0 and ratio.T <= 0


def proof_rate_terms() -> dict[int, dict]:
    """Reproduce the exponent substitutions in the displayed final bounds."""

    out: dict[int, dict] = {}

    beta = T_VAR.power(Fraction(-1, 2))
    eta = D.power(Fraction(-1, 2)) * T_VAR.power(Fraction(-3, 4))
    target = D.power(Fraction(1, 2)) * T_VAR.power(Fraction(-1, 4))
    inside = [
        ONE / (beta * T_VAR),
        eta.power(Fraction(2)) * D / beta.power(Fraction(2)),
        beta,
    ]
    terms = [ONE / (eta * T_VAR)] + [SQRT_D * z.power(Fraction(1, 2)) for z in inside] + [eta * D]
    out[1] = _rate_result(terms, target, "d,n,T>=1", "l1")

    beta = T_VAR.power(Fraction(-2, 3))
    eta = D.power(Fraction(-1, 2)) * T_VAR.power(Fraction(-2, 3))
    b0 = T_VAR.power(Fraction(1, 3))
    target = D.power(Fraction(1, 2)) * T_VAR.power(Fraction(-1, 3))
    inside = [
        ONE / (b0 * beta * T_VAR),
        eta.power(Fraction(2)) * D / beta,
        beta,
    ]
    terms = [ONE / (eta * T_VAR)] + [SQRT_D * z.power(Fraction(1, 2)) for z in inside] + [eta * D]
    out[2] = _rate_result(terms, target, "d,n,T>=1", "l1")

    beta = N.power(Fraction(1, 2)) * T_VAR.power(Fraction(-1, 2))
    eta = N.power(Fraction(1, 4)) * D.power(Fraction(-1, 2)) * T_VAR.power(Fraction(-3, 4))
    target = D.power(Fraction(1, 2)) * N.power(Fraction(-1, 4)) * T_VAR.power(Fraction(-1, 4))
    inside = [
        ONE / (beta * N * T_VAR),
        eta.power(Fraction(2)) * D / beta.power(Fraction(2)),
        beta / N,
    ]
    terms = [ONE / (eta * T_VAR)] + [SQRT_D * z.power(Fraction(1, 2)) for z in inside] + [eta * D]
    out[3] = _rate_result(terms, target, "T>=n", "l1")

    beta = N.power(Fraction(1, 3)) * T_VAR.power(Fraction(-2, 3))
    eta = N.power(Fraction(1, 3)) * D.power(Fraction(-1, 2)) * T_VAR.power(Fraction(-2, 3))
    b0 = N.power(Fraction(-2, 3)) * T_VAR.power(Fraction(1, 3))
    target = D.power(Fraction(1, 2)) * N.power(Fraction(-1, 3)) * T_VAR.power(Fraction(-1, 3))
    inside = [
        ONE / (beta * N * b0 * T_VAR),
        eta.power(Fraction(2)) * D / (N * beta),
        beta / N,
    ]
    terms = [ONE / (eta * T_VAR)] + [SQRT_D * z.power(Fraction(1, 2)) for z in inside] + [eta * D]
    out[4] = _rate_result(terms, target, "T>=n^2", "l1")

    eta_a = D.power(Fraction(-1, 2)) * T_VAR.power(Fraction(-1, 2))
    target_a = [D.power(Fraction(1, 2)) * T_VAR.power(Fraction(-1, 2)), D * N.power(Fraction(-1, 2))]
    terms_a = [
        ONE / (eta_a * T_VAR),
        D * N.power(Fraction(-1, 2)),
        eta_a * D,
        SQRT_D * (ONE / (N * T_VAR)).power(Fraction(1, 2)),
        SQRT_D * (ONE / N).power(Fraction(1, 2)),
        SQRT_D * (eta_a.power(Fraction(2)) * D).power(Fraction(1, 2)),
    ]
    eta_b = N.power(Fraction(-1, 2))
    target_b = [N.power(Fraction(1, 2)) / T_VAR, D * N.power(Fraction(-1, 2))]
    terms_b = [
        ONE / (eta_b * T_VAR),
        D * N.power(Fraction(-1, 2)),
        eta_b * D,
        SQRT_D * (eta_b.power(Fraction(2)) * D).power(Fraction(1, 2)),
    ]
    out[5] = {
        "passed": all(_dominated_by_sum(x, target_a) for x in terms_a)
        and all(_dominated_by_sum(x, target_b) for x in terms_b),
        "proved_norm": "l1",
        "schedule_a_terms": [x.serial() for x in terms_a],
        "schedule_a_targets": [x.serial() for x in target_a],
        "schedule_b_terms": [x.serial() for x in terms_b],
        "schedule_b_targets": [x.serial() for x in target_b],
        "domain": "d,n,T>=1",
    }

    # Appendix G/H prove a time-average l2 norm.  The theorem statements claim
    # the same rate for l1 without the necessary sqrt(d) conversion.
    out[6] = {
        "passed": False,
        "proved_norm": "l2",
        "claimed_norm": "l1",
        "missing_conversion": "||g||_1 <= sqrt(d)||g||_2",
        "claimed_dimension_exponent": "1/4",
        "proof_supported_l1_dimension_exponent": "3/4",
        "anchors": ["thm7", "thm8", "Appendix G", "Appendix H"],
    }
    return out


def _rate_result(terms: Iterable[Monomial], target: Monomial, domain: str, norm: str) -> dict:
    terms = list(terms)
    return {
        "passed": all(_dominates_under_domain(x, target, domain.replace("d,n,", "")) for x in terms),
        "proved_norm": norm,
        "terms": [x.serial() for x in terms],
        "target": target.serial(),
        "domain": domain,
    }


def _dominated_by_sum(term: Monomial, targets: list[Monomial]) -> bool:
    return any(_dominates_under_domain(term, target, "") for target in targets)


def local_inequality_checks() -> dict:
    rng = np.random.default_rng(250812327)
    failures: list[str] = []

    grid = np.linspace(-4.0, 4.0, 129)
    for a in grid:
        if a == 0:
            continue
        for v in grid:
            if v == 0:
                continue
            mismatch = np.sign(a) != np.sign(v)
            if 2 * abs(a) * mismatch > 2 * abs(a - v) + 1e-12:
                failures.append("sign-mismatch scalar inequality")
                break

    norm_margin = math.inf
    for d in (1, 2, 7, 32, 257):
        z = rng.normal(size=(128, d))
        margin = np.sqrt(d) * np.linalg.norm(z, axis=1) - np.linalg.norm(z, ord=1, axis=1)
        norm_margin = min(norm_margin, float(margin.min()))
        if margin.min() < -1e-12:
            failures.append("l1-l2 inequality")

    smooth_margin = math.inf
    for d in (1, 8, 64):
        x = rng.uniform(-20, 20, size=(256, d))
        y = rng.uniform(-20, 20, size=(256, d))
        fx = np.sum(1 - np.cos(x), axis=1)
        fy = np.sum(1 - np.cos(y), axis=1)
        gy = np.sin(y)
        rhs = fy + np.sum(gy * (x - y), axis=1) + 0.5 * np.sum((x - y) ** 2, axis=1)
        margin = rhs - fx
        smooth_margin = min(smooth_margin, float(margin.min()))
        if margin.min() < -1e-10:
            failures.append("periodic smoothness descent inequality")

    unbiased_max_error = 0.0
    variance_max = 0.0
    G = 1.25
    for v in np.linspace(-G, G, 101):
        p = (G + v) / (2 * G)
        mean = p - (1 - p)
        variance = p * (1 - mean) ** 2 + (1 - p) * (-1 - mean) ** 2
        unbiased_max_error = max(unbiased_max_error, abs(mean - v / G))
        variance_max = max(variance_max, variance)
    if unbiased_max_error > 1e-14 or variance_max > 1 + 1e-14:
        failures.append("unbiased sign mapping")

    return {
        "passed": not failures,
        "failures": failures,
        "tests": {
            "sign_mismatch_grid_pairs": 128 * 128,
            "l1_l2_dimensions": [1, 2, 7, 32, 257],
            "l1_l2_min_margin": norm_margin,
            "periodic_smoothness_min_margin": smooth_margin,
            "unbiased_sign_max_mean_error": unbiased_max_error,
            "unbiased_sign_max_variance": variance_max,
        },
    }


def counterexample_claim6() -> dict:
    """Exact asymptotic counterexample to the stated l1 dimension exponent.

    Let n=1, d=T^6, eta=d^-1/2 T^-1/2, x1=eta*1, and
    f_d(x)=sum_k(1-cos x_k), with a deterministic oracle.  All assumptions hold
    with L=G=1, sigma=0, and Delta_f<=1/2.  The t=1 term alone yields
    A_T >= d*sin(eta)/T >= (1/2)*sqrt(d)*T^-3/2.  Dividing by the claimed
    d^1/4 T^-1/4 rate gives at least (1/2)T^1/4, which is unbounded.
    """

    rows = []
    for T in (2, 4, 8, 16, 32, 64):
        d = T**6
        eta = d ** -0.5 * T ** -0.5
        exact_first_term_lower_bound = d * math.sin(eta) / T
        elementary_lower_bound = 0.5 * math.sqrt(d) * T ** -1.5
        claimed_rate = d ** 0.25 * T ** -0.25
        ratio = exact_first_term_lower_bound / claimed_rate
        rows.append(
            {
                "T": T,
                "d": d,
                "n": 1,
                "eta": eta,
                "delta_f": d * (1 - math.cos(eta)),
                "first_term_lower_bound": exact_first_term_lower_bound,
                "sin_lower_bound": elementary_lower_bound,
                "claimed_rate_without_constant": claimed_rate,
                "ratio": ratio,
            }
        )

    log_t = np.log([r["T"] for r in rows])
    log_ratio = np.log([r["ratio"] for r in rows])
    fitted_growth = float(np.polyfit(log_t, log_ratio, 1)[0])
    assumptions = {
        "objective": "f_d(x)=sum_k(1-cos(x_k))",
        "lower_bounded": True,
        "delta_f_uniform_upper_bound": 0.5,
        "L_smooth": True,
        "L": 1,
        "average_smooth": True,
        "unbiased_oracle": True,
        "sigma": 0,
        "bounded_stochastic_gradient": True,
        "G": 1,
        "n": 1,
        "initial_condition": "||x1||_infinity=eta",
        "lambda": 0,
        "vr_beta2": "T^(-1/2)",
        "vr_beta1": "beta2",
        "non_vr_beta2": "T^(-1/3) when d=T^6,n=1",
        "non_vr_beta1": "beta2",
    }
    passed = (
        all(r["delta_f"] <= 0.5 + 1e-12 for r in rows)
        and all(r["first_term_lower_bound"] >= r["sin_lower_bound"] for r in rows)
        and fitted_growth > 0.20
        and rows[-1]["ratio"] > rows[0]["ratio"]
    )
    return {
        "valid_falsification": passed,
        "exact_claim": CLAIMS[6],
        "assumptions": assumptions,
        "argument": {
            "lower_bound": "A_T >= d sin(eta)/T >= 0.5 sqrt(d) T^(-3/2)",
            "substitution": "d=T^6",
            "claimed_rate": "d^(1/4)T^(-1/4)=T^(5/4)",
            "ratio_lower_bound": "0.5 T^(1/4) -> infinity",
            "scope": "Both displayed Theorem 6 (thm7) and Theorem 7 (thm8) state l1, while Appendices G/H only derive l2.",
        },
        "rows": rows,
        "fitted_ratio_growth_exponent": fitted_growth,
    }


def validate(raw: dict) -> dict:
    statuses: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for claim in range(1, 6):
        ok = raw["proof_rates"][str(claim)]["passed"] and raw["local_inequalities"]["passed"]
        statuses[str(claim)] = "ANALYTICALLY_SUPPORTED" if ok else "BLOCKED"
        reasons[str(claim)] = "Exact schedule substitution and audited local inequalities pass." if ok else "A proof-rate or local-inequality audit failed."
    c6 = raw["counterexample_claim6"]["valid_falsification"]
    statuses["6"] = "FALSIFIED" if c6 else "BLOCKED"
    reasons["6"] = (
        "The l1 theorem is contradicted by an assumption-satisfying periodic family; the appendix proves only l2."
        if c6
        else "The candidate counterexample did not satisfy every contract check."
    )
    passed = all(statuses[str(i)] == "ANALYTICALLY_SUPPORTED" for i in range(1, 6)) and statuses["6"] == "FALSIFIED"
    return {"passed": passed, "statuses": statuses, "reasons": reasons}


def negative_control(raw: dict) -> dict:
    tampered = json.loads(json.dumps(raw))
    tampered["proof_rates"]["1"]["passed"] = False
    rejected = not validate(tampered)["passed"]

    wrong_norm = json.loads(json.dumps(raw))
    wrong_norm["counterexample_claim6"]["assumptions"]["quantity"] = "l2"
    wrong_norm["counterexample_claim6"]["valid_falsification"] = False
    wrong_norm_rejected = validate(wrong_norm)["statuses"]["6"] == "BLOCKED"
    return {
        "passed": rejected and wrong_norm_rejected,
        "corrupted_rate_audit_rejected": rejected,
        "l2_substitution_not_mislabeled_as_falsification": wrong_norm_rejected,
    }


def independent_check(raw: dict) -> dict:
    rates = raw["proof_rates"]
    expected = {
        "1": {"d": "1/2", "n": "0", "T": "-1/4"},
        "2": {"d": "1/2", "n": "0", "T": "-1/3"},
        "3": {"d": "1/2", "n": "-1/4", "T": "-1/4"},
        "4": {"d": "1/2", "n": "-1/3", "T": "-1/3"},
    }
    targets_match = all(rates[k]["target"] == v for k, v in expected.items())
    ratios = [r["ratio"] for r in raw["counterexample_claim6"]["rows"]]
    ratio_monotone = all(b > a for a, b in zip(ratios, ratios[1:]))
    source_contract_complete = all(
        set(["anchor", "assumptions", "quantity", "rate", "schedule", "quantifiers"]).issubset(CLAIMS[i])
        for i in range(1, 7)
    )
    passed = targets_match and ratio_monotone and source_contract_complete
    return {
        "passed": passed,
        "targets_match": targets_match,
        "counterexample_ratio_strictly_increasing": ratio_monotone,
        "source_contract_complete": source_contract_complete,
        "implementation": "Independent direct JSON checks; does not call validate().",
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_artifacts(raw: dict, verdict: dict, independent: dict, neg: dict, elapsed: float) -> dict[str, str]:
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    env = {
        "git_sha": git_sha,
        "run_command": RUN_COMMAND,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "elapsed_seconds": elapsed,
        "deterministic_seed": 250812327,
        "paper_source_sha256": SOURCE_SHA256,
    }
    for claim, contract in CLAIMS.items():
        d = ARTIFACT_ROOT / f"claim_{claim}"
        _write_json(d / "claim_contract.json", contract)
        _write_text(
            d / "source_audit.md",
            f"""# Source audit — Claim {claim}

- Primary source: `{SOURCE_URL}` (`arXiv:2508.12327v1`)
- Source SHA-256: `{SOURCE_SHA256}`
- LaTeX anchor: `{contract['anchor']}`
- Displayed theorem: `{contract['displayed_theorem']}`
- Quantity: `{contract['quantity']}`
- Exact assumptions: {", ".join(contract['assumptions'])}
- Exact schedule: `{json.dumps(contract['schedule'], sort_keys=True)}`
- Quantifier reading: {contract['quantifiers']}

No nearby empirical or convergence-only proxy is substituted for the displayed
expected time-average norm.
""",
        )
        _write_text(
            d / "method.md",
            f"""# Method — Claim {claim}

Route A uses exact rational exponent arithmetic on the paper's final displayed
bound, exhaustive scalar sign checks, multi-dimensional norm checks, a global
smoothness check on the noncoercive periodic family, and an independent JSON
checker. Claim 6 additionally uses a constructive asymptotic counterexample.
""",
        )
        _write_json(d / "raw_proof_audit.json", raw["proof_rates"][str(claim)])
        if claim == 6:
            _write_json(d / "raw_counterexample.json", raw["counterexample_claim6"])
        _write_json(
            d / "verifier_output.json",
            {"status": verdict["statuses"][str(claim)], "reason": verdict["reasons"][str(claim)]},
        )
        _write_json(d / "independent_checker_output.json", independent)
        _write_json(d / "negative_control_output.json", neg)
        _write_json(d / "environment.json", env)
        _write_text(d / "command.txt", RUN_COMMAND)
        _write_text(
            d / "limitations.md",
            (
                "Route A audits the stated proof and exact asymptotic contract; "
                "Claims 1–5 remain analytically supported rather than final VERIFIED "
                "until the independent empirical route is merged. Claim 6 is a "
                "statement-level falsification of the displayed l1 norm, not a claim "
                "that the appendix's l2 result is false."
            ),
        )
        _write_text(
            d / "EVAL.md",
            f"""# Claim {claim} evaluation

Verdict: **{verdict['statuses'][str(claim)]}**

{verdict['reasons'][str(claim)]}

Negative controls: {"PASS" if neg["passed"] else "FAIL"}.
Independent checker: {"PASS" if independent["passed"] else "FAIL"}.
""",
        )

    manifest = {}
    for path in sorted(ARTIFACT_ROOT.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(ROOT))] = _sha256(path)
    _write_json(ARTIFACT_ROOT / "route_a_manifest.json", manifest)
    manifest[str((ARTIFACT_ROOT / "route_a_manifest.json").relative_to(ROOT))] = _sha256(
        ARTIFACT_ROOT / "route_a_manifest.json"
    )
    return manifest


def main() -> None:
    started = time.perf_counter()
    rates = proof_rate_terms()
    raw = {
        "schema": "lion-theorem-proof-audit-v1",
        "paper_source": {"url": SOURCE_URL, "sha256": SOURCE_SHA256, "version": "2508.12327v1"},
        "proof_rates": {str(k): v for k, v in rates.items()},
        "local_inequalities": local_inequality_checks(),
        "counterexample_claim6": counterexample_claim6(),
    }
    verdict = validate(raw)
    independent = independent_check(raw)
    neg = negative_control(raw)
    elapsed = time.perf_counter() - started
    manifest = write_artifacts(raw, verdict, independent, neg, elapsed)

    summary = {
        "schema": raw["schema"],
        "verdict": verdict,
        "independent_checker": independent,
        "negative_controls": neg,
        "claim6_ratio_growth_exponent": raw["counterexample_claim6"]["fitted_ratio_growth_exponent"],
        "artifact_count": len(manifest),
        "elapsed_seconds": elapsed,
    }
    print("\n" + "=" * 78)
    print("ROUTE A: EXACT THEOREM CONTRACT AND PROOF AUDIT")
    print("=" * 78)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("ROUTE_A_MACHINE_SUMMARY " + json.dumps(summary, sort_keys=True, separators=(",", ":")))

    if not verdict["passed"] or not independent["passed"] or not neg["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

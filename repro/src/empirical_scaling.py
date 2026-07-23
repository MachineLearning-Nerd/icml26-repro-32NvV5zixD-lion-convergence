"""Multi-axis empirical rate checks for arXiv:2508.12327v1.

The experiments use the globally 1-smooth, lower-bounded, noncoercive family

    f_j(x) = sum_k (1 - cos(x_k - phi_j))

with symmetric heterogeneous worker phases and additive bounded Rademacher
noise.  The same sample is evaluated at x_t and x_{t-1} in every STORM
correction, so the average-smoothness assumption holds exactly.  All reported
metrics are the theorem quantity: the time-average true-gradient l1 norm.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".openresearch" / "artifacts"
RUN_COMMAND = "uv run --frozen python repro/src/verify_lion.py"
SOURCE_SHA256 = "cca5c0649acd36faff8eb63857d25811b009c6ad9ffa4b8810ae65e27b625688"
MASTER_SEED = 250812327
NOISE_L2 = 0.25
G_BOUND = 1.25
PHASE_AMPLITUDE = 0.60

T_GRID_CENTRAL = [256, 512, 1024, 2048, 4096]
D_GRID_CENTRAL = [16, 64, 256]
T_GRID_DISTRIBUTED = [256, 512, 1024, 2048]
D_GRID_DISTRIBUTED = [32, 128]
N_GRID_DISTRIBUTED = [2, 4, 8]
T_GRID_COMPRESSION = [256, 1024, 4096]
D_GRID_COMPRESSION = [16, 64]
N_GRID_COMPRESSION = [3, 9]


def _config_seed(*parts: object) -> int:
    raw = "|".join(map(str, (MASTER_SEED,) + parts)).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "little")


def _phases(n: int) -> np.ndarray:
    if n == 1:
        return np.zeros((1, 1))
    p = np.linspace(-PHASE_AMPLITUDE, PHASE_AMPLITUDE, n, dtype=np.float64)
    p -= p.mean()
    return p[:, None]


def _true_worker_grad(x: np.ndarray, phases: np.ndarray) -> np.ndarray:
    return np.sin(x[:, None, :] - phases[None, :, :])


def _noise(rng: np.random.Generator, shape: tuple[int, ...], d: int) -> np.ndarray:
    signs = rng.integers(0, 2, size=shape, dtype=np.int8)
    return (signs.astype(np.float64) * 2.0 - 1.0) * (NOISE_L2 / math.sqrt(d))


def _batch_noise(
    rng: np.random.Generator, samples: int, shape: tuple[int, ...], d: int
) -> np.ndarray:
    if samples <= 1:
        return _noise(rng, shape, d)
    total = np.zeros(shape, dtype=np.float64)
    for _ in range(samples):
        total += _noise(rng, shape, d)
    return total / samples


def _unbiased_sign(rng: np.random.Generator, value: np.ndarray, radius: float) -> np.ndarray:
    if float(np.max(np.abs(value))) > radius + 1e-12:
        raise AssertionError("unbiased-sign input exceeds certified radius")
    probability = np.clip((radius + value) / (2 * radius), 0.0, 1.0)
    return np.where(rng.random(value.shape) < probability, 1.0, -1.0)


def _parameters(claim: int, d: int, T: int, n: int, schedule: str) -> dict:
    if claim == 1:
        beta2 = 0.5 * T ** -0.5
        return {"beta1": beta2, "beta2": beta2, "eta": 0.5 * d ** -0.5 * T ** -0.75, "B0": 1}
    if claim == 2:
        beta2 = 0.5 * T ** (-2 / 3)
        return {
            "beta1": beta2,
            "beta2": beta2,
            "eta": 0.5 * d ** -0.5 * T ** (-2 / 3),
            "B0": max(1, math.ceil(T ** (1 / 3))),
        }
    if claim == 3:
        beta2 = 0.5 * n ** 0.5 * T ** -0.5
        return {
            "beta1": beta2,
            "beta2": beta2,
            "eta": 0.5 * n ** 0.25 * d ** -0.5 * T ** -0.75,
            "B0": 1,
        }
    if claim == 4:
        beta2 = 0.5 * n ** (1 / 3) * T ** (-2 / 3)
        return {
            "beta1": beta2,
            "beta2": beta2,
            "eta": 0.5 * n ** (1 / 3) * d ** -0.5 * T ** (-2 / 3),
            "B0": max(1, math.ceil(n ** (-2 / 3) * T ** (1 / 3))),
        }
    if claim == 5 and schedule == "eta_T":
        return {"beta1": 0.5, "beta2": 0.5, "eta": 0.5 * d ** -0.5 * T ** -0.5, "B0": 1}
    if claim == 5 and schedule == "eta_n":
        return {"beta1": 0.5, "beta2": 0.5, "eta": 0.25 * n ** -0.5, "B0": 1}
    raise ValueError((claim, schedule))


def run_configuration(
    claim: int,
    d: int,
    T: int,
    n: int,
    seeds: int,
    schedule: str = "paper",
) -> tuple[list[dict], dict]:
    """Run one vectorized seed block and return seed rows plus diagnostics."""

    if claim in (1, 2):
        n = 1
    params = _parameters(claim, d, T, n, schedule)
    beta1, beta2, eta, B0 = (
        params["beta1"],
        params["beta2"],
        params["eta"],
        params["B0"],
    )
    rng = np.random.default_rng(_config_seed(claim, d, T, n, schedule))
    phases = _phases(n)
    x0 = eta if claim in (1, 2, 3, 4) else 0.75
    x = np.full((seeds, d), x0, dtype=np.float64)
    previous_x = x.copy()
    true_workers = _true_worker_grad(x, phases)
    initial_noise = _batch_noise(rng, B0, true_workers.shape, d)
    m = true_workers + initial_noise
    v = m.copy()

    l1_sum = np.zeros(seeds)
    l2_sum = np.zeros(seeds)
    max_stochastic_coordinate = float(np.max(np.abs(m)))
    noise_sum = float(initial_noise.sum())
    noise_square_sum = float(np.square(initial_noise).sum())
    noise_count = int(initial_noise.size)
    max_average_smooth_ratio = 0.0

    for _ in range(T):
        true_workers = _true_worker_grad(x, phases)
        true_global = true_workers.mean(axis=1)
        l1_sum += np.linalg.norm(true_global, ord=1, axis=1)
        l2_sum += np.linalg.norm(true_global, axis=1)

        eps = _noise(rng, true_workers.shape, d)
        stochastic = true_workers + eps
        max_stochastic_coordinate = max(max_stochastic_coordinate, float(np.max(np.abs(stochastic))))
        noise_sum += float(eps.sum())
        noise_square_sum += float(np.square(eps).sum())
        noise_count += int(eps.size)

        if claim in (2, 4):
            previous_true = _true_worker_grad(previous_x, phases)
            correction = true_workers - previous_true
            dx = x - previous_x
            denom = np.square(dx).sum(axis=1)
            numer = np.square(correction).sum(axis=(1, 2)) / n
            mask = denom > 0
            if np.any(mask):
                max_average_smooth_ratio = max(
                    max_average_smooth_ratio, float(np.max(numer[mask] / denom[mask]))
                )
        else:
            correction = np.zeros_like(stochastic)

        if claim in (1, 3, 5):
            v = (1 - beta1) * m + beta1 * stochastic
            new_m = (1 - beta2) * m + beta2 * stochastic
        elif claim in (2, 4):
            v = (1 - beta1) * m + beta1 * stochastic
            if claim == 4:
                v = v + (1 - beta1) * correction
            new_m = (1 - beta2) * m + beta2 * stochastic + (1 - beta2) * correction
        else:
            raise ValueError(claim)

        if claim == 5:
            upload = _unbiased_sign(rng, v, G_BOUND)
            direction = np.sign(upload.mean(axis=1))
            if np.any(direction == 0):
                raise AssertionError("odd worker count should prevent majority ties")
        else:
            direction = np.sign(v.mean(axis=1))

        old_x = x
        x = x - eta * direction
        previous_x = old_x
        m = new_m

    expected_noise_variance = NOISE_L2**2
    empirical_noise_mean = noise_sum / noise_count
    empirical_noise_l2_variance = d * noise_square_sum / noise_count
    rows = []
    for lane in range(seeds):
        rows.append(
            {
                "claim": claim,
                "schedule": schedule,
                "seed_lane": lane,
                "stream_seed": _config_seed(claim, d, T, n, schedule),
                "d": d,
                "n": n,
                "T": T,
                "beta1": beta1,
                "beta2": beta2,
                "eta": eta,
                "B0": B0,
                "avg_grad_l1": float(l1_sum[lane] / T),
                "avg_grad_l2": float(l2_sum[lane] / T),
            }
        )
    diagnostics = {
        "claim": claim,
        "schedule": schedule,
        "d": d,
        "n": n,
        "T": T,
        "max_stochastic_coordinate": max_stochastic_coordinate,
        "certified_G": G_BOUND,
        "empirical_noise_coordinate_mean": empirical_noise_mean,
        "empirical_noise_l2_variance": empirical_noise_l2_variance,
        "certified_noise_l2_variance": expected_noise_variance,
        "max_average_smooth_ratio": max_average_smooth_ratio,
        "certified_L": 1.0,
        "objective_lower_bound": 0.0,
        "noncoercive_witness": "f(2*pi*k*1)=0 for arbitrarily large integer k",
        "initial_linf": x0,
        "initial_condition_required": claim in (1, 2, 3, 4),
        "initial_condition_satisfied": (x0 <= eta + 1e-15) if claim in (1, 2, 3, 4) else None,
        "T_domain_satisfied": (T >= n if claim == 3 else T >= n * n if claim == 4 else True),
    }
    return rows, diagnostics


def _mean_groups(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        key = (row["claim"], row["schedule"], row["d"], row["n"], row["T"])
        grouped[key].append(row["avg_grad_l1"])
    out = []
    for key, values in sorted(grouped.items()):
        array = np.asarray(values)
        out.append(
            {
                "claim": key[0],
                "schedule": key[1],
                "d": key[2],
                "n": key[3],
                "T": key[4],
                "mean": float(array.mean()),
                "std": float(array.std(ddof=1)),
                "se": float(array.std(ddof=1) / math.sqrt(len(array))),
                "ci95_low": float(array.mean() - 1.96 * array.std(ddof=1) / math.sqrt(len(array))),
                "ci95_high": float(array.mean() + 1.96 * array.std(ddof=1) / math.sqrt(len(array))),
                "seeds": len(array),
            }
        )
    return out


def _bootstrap_slope(
    rows: list[dict], claim: int, schedule: str, d: int, n: int, rounds: int = 400
) -> dict:
    selected = [
        r for r in rows if r["claim"] == claim and r["schedule"] == schedule and r["d"] == d and r["n"] == n
    ]
    by_t: dict[int, list[float]] = defaultdict(list)
    for row in selected:
        by_t[row["T"]].append(row["avg_grad_l1"])
    ts = np.array(sorted(by_t), dtype=float)
    means = np.array([np.mean(by_t[int(t)]) for t in ts])
    slope = float(np.polyfit(np.log(ts), np.log(means), 1)[0])
    rng = np.random.default_rng(_config_seed("bootstrap", claim, schedule, d, n))
    slopes = []
    for _ in range(rounds):
        boot_means = []
        for t in ts:
            values = np.asarray(by_t[int(t)])
            boot_means.append(float(np.mean(rng.choice(values, size=len(values), replace=True))))
        slopes.append(float(np.polyfit(np.log(ts), np.log(boot_means), 1)[0]))
    return {
        "claim": claim,
        "schedule": schedule,
        "d": d,
        "n": n,
        "slope": slope,
        "ci95_low": float(np.quantile(slopes, 0.025)),
        "ci95_high": float(np.quantile(slopes, 0.975)),
        "T_values": [int(x) for x in ts],
    }


def _rate_formula(row: dict) -> float:
    d, n, T = row["d"], row["n"], row["T"]
    if row["claim"] == 1:
        return math.sqrt(d) * T ** -0.25
    if row["claim"] == 2:
        return math.sqrt(d) * T ** (-1 / 3)
    if row["claim"] == 3:
        return math.sqrt(d) * (n * T) ** -0.25
    if row["claim"] == 4:
        return math.sqrt(d) * (n * T) ** (-1 / 3)
    if row["claim"] == 5 and row["schedule"] == "eta_T":
        return math.sqrt(d) * T ** -0.5 + d * n ** -0.5
    if row["claim"] == 5 and row["schedule"] == "eta_n":
        return math.sqrt(n) / T + d * n ** -0.5
    raise ValueError(row)


def summarize(rows: list[dict], diagnostics: list[dict]) -> dict:
    aggregate = _mean_groups(rows)
    slopes = []
    for claim, target in ((1, -0.25), (2, -1 / 3)):
        for d in D_GRID_CENTRAL:
            item = _bootstrap_slope(rows, claim, "paper", d, 1)
            item["target_upper_exponent"] = target
            item["passes"] = item["ci95_high"] <= target + 0.15
            slopes.append(item)
    for claim, target in ((3, -0.25), (4, -1 / 3)):
        for d in D_GRID_DISTRIBUTED:
            for n in N_GRID_DISTRIBUTED:
                item = _bootstrap_slope(rows, claim, "paper", d, n)
                item["target_upper_exponent"] = target
                item["passes"] = item["ci95_high"] <= target + 0.15
                slopes.append(item)

    ratios_by_claim: dict[int, list[float]] = defaultdict(list)
    normalized_rows = []
    for row in aggregate:
        ratio = row["mean"] / _rate_formula(row)
        ratios_by_claim[row["claim"]].append(ratio)
        normalized_rows.append({**row, "rate_formula": _rate_formula(row), "normalized_ratio": ratio})

    assumption_checks = {
        "max_stochastic_coordinate_within_G": max(d["max_stochastic_coordinate"] for d in diagnostics) <= G_BOUND + 1e-12,
        "max_stochastic_coordinate": max(d["max_stochastic_coordinate"] for d in diagnostics),
        "G": G_BOUND,
        "max_abs_empirical_noise_mean": max(abs(d["empirical_noise_coordinate_mean"]) for d in diagnostics),
        "max_noise_variance_error": max(
            abs(d["empirical_noise_l2_variance"] - d["certified_noise_l2_variance"]) for d in diagnostics
        ),
        "max_average_smooth_ratio": max(d["max_average_smooth_ratio"] for d in diagnostics),
        "average_smooth_L": 1.0,
        "all_initial_conditions": all(
            d["initial_condition_satisfied"] is not False for d in diagnostics
        ),
        "all_T_domains": all(d["T_domain_satisfied"] for d in diagnostics),
        "lower_bounded": True,
        "noncoercive": True,
    }
    assumption_checks["passed"] = (
        assumption_checks["max_stochastic_coordinate_within_G"]
        and assumption_checks["max_abs_empirical_noise_mean"] < 0.01
        and assumption_checks["max_noise_variance_error"] < 0.01
        and assumption_checks["max_average_smooth_ratio"] <= 1.0 + 1e-10
        and assumption_checks["all_initial_conditions"]
        and assumption_checks["all_T_domains"]
    )

    statuses = {}
    for claim in range(1, 5):
        selected = [x for x in slopes if x["claim"] == claim]
        ratio_values = ratios_by_claim[claim]
        statuses[str(claim)] = {
            "status": "EMPIRICALLY_SUPPORTED"
            if selected and all(x["passes"] for x in selected) and max(ratio_values) / min(ratio_values) < 8
            else "INCONCLUSIVE",
            "all_slope_checks": bool(selected) and all(x["passes"] for x in selected),
            "normalized_ratio_range": [min(ratio_values), max(ratio_values)],
        }

    c5_ratios = ratios_by_claim[5]
    # The theorem contains a non-vanishing n-dependent floor.  Directly fit
    # the complete two-term formula rather than pretending it is a pure T law.
    statuses["5"] = {
        "status": "EMPIRICALLY_SUPPORTED"
        if max(c5_ratios) / min(c5_ratios) < 8
        else "INCONCLUSIVE",
        "normalized_ratio_range": [min(c5_ratios), max(c5_ratios)],
        "criterion": "mean divided by the complete two-term theorem rate across both eta schedules",
    }
    passed = assumption_checks["passed"] and all(
        statuses[str(i)]["status"] == "EMPIRICALLY_SUPPORTED" for i in range(1, 6)
    )
    return {
        "passed": passed,
        "statuses": statuses,
        "assumptions": assumption_checks,
        "slopes": slopes,
        "aggregate": normalized_rows,
    }


def independent_check(rows: list[dict], summary: dict) -> dict:
    recomputed = _mean_groups(rows)
    stored = {
        (r["claim"], r["schedule"], r["d"], r["n"], r["T"]): r["mean"]
        for r in summary["aggregate"]
    }
    max_mean_error = 0.0
    for row in recomputed:
        key = (row["claim"], row["schedule"], row["d"], row["n"], row["T"])
        max_mean_error = max(max_mean_error, abs(row["mean"] - stored[key]))
    coverage = {
        "claims": sorted(set(r["claim"] for r in rows)),
        "seed_rows": len(rows),
        "central_dimensions": sorted(set(r["d"] for r in rows if r["claim"] in (1, 2))),
        "distributed_nodes": sorted(set(r["n"] for r in rows if r["claim"] in (3, 4))),
        "compression_schedules": sorted(set(r["schedule"] for r in rows if r["claim"] == 5)),
    }
    passed = (
        max_mean_error < 1e-12
        and coverage["claims"] == [1, 2, 3, 4, 5]
        and coverage["compression_schedules"] == ["eta_T", "eta_n"]
    )
    return {
        "passed": passed,
        "max_recomputed_mean_error": max_mean_error,
        "coverage": coverage,
        "implementation": "Independent group-by recomputation from seed-level rows.",
    }


def negative_control(rows: list[dict], diagnostics: list[dict]) -> dict:
    corrupted = json.loads(json.dumps(rows))
    for row in corrupted:
        if row["claim"] == 1 and row["T"] == max(T_GRID_CENTRAL):
            row["avg_grad_l1"] *= 100.0
    corrupted_summary = summarize(corrupted, diagnostics)
    rate_corruption_rejected = corrupted_summary["statuses"]["1"]["status"] == "INCONCLUSIVE"

    bad_diagnostics = json.loads(json.dumps(diagnostics))
    bad_diagnostics[0]["max_stochastic_coordinate"] = G_BOUND * 2
    assumption_summary = summarize(rows, bad_diagnostics)
    assumption_corruption_rejected = not assumption_summary["assumptions"]["passed"]
    return {
        "passed": rate_corruption_rejected and assumption_corruption_rejected,
        "corrupted_final_horizon_rejected": rate_corruption_rejected,
        "bounded_gradient_violation_rejected": assumption_corruption_rejected,
    }


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_artifacts(
    rows: list[dict],
    diagnostics: list[dict],
    summary: dict,
    independent: dict,
    negative: dict,
    elapsed: float,
) -> dict[str, str]:
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
        "master_seed": MASTER_SEED,
        "paper_source_sha256": SOURCE_SHA256,
    }
    for claim in range(1, 6):
        d = ARTIFACT_ROOT / f"claim_{claim}"
        claim_rows = [r for r in rows if r["claim"] == claim]
        claim_diag = [r for r in diagnostics if r["claim"] == claim]
        _write_csv(d / "raw_empirical.csv", claim_rows)
        _write_json(d / "assumption_measurements.json", claim_diag)
        _write_json(d / "empirical_summary.json", summary["statuses"][str(claim)])
        _write_json(d / "independent_checker_output.json", independent)
        _write_json(d / "negative_control_output.json", negative)
        _write_json(d / "environment.json", env)
        _write_text(d / "command.txt", RUN_COMMAND)
        _write_text(
            d / "method.md",
            f"""# Empirical method — Claim {claim}

The exact paper schedule is run on globally smooth noncoercive periodic
objectives with bounded unbiased Rademacher gradient noise. The theorem's
time-average true-gradient l1 norm is retained for every deterministic seed
lane. Rate exponents use log-log fits with 400 bootstrap resamples. Claim 5 is
checked against both complete two-term formulas, including its n-dependent
floor.
""",
        )
        _write_text(
            d / "limitations.md",
            "A finite multi-axis family cannot establish a universal theorem by itself. "
            "This route is therefore combined with the exact proof audit; it is not "
            "described as a full-scale application benchmark.",
        )
        _write_text(
            d / "EVAL.md",
            f"""# Claim {claim} empirical evaluation

Status: **{summary['statuses'][str(claim)]['status']}**

Assumptions measured: {"PASS" if summary['assumptions']['passed'] else "FAIL"}.
Independent checker: {"PASS" if independent['passed'] else "FAIL"}.
Negative controls: {"PASS" if negative['passed'] else "FAIL"}.
""",
        )
    manifest = {}
    for path in sorted(ARTIFACT_ROOT.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(ROOT))] = _sha(path)
    _write_json(ARTIFACT_ROOT / "route_b_manifest.json", manifest)
    manifest[str((ARTIFACT_ROOT / "route_b_manifest.json").relative_to(ROOT))] = _sha(
        ARTIFACT_ROOT / "route_b_manifest.json"
    )
    return manifest


def _rows_as_compact_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> None:
    started = time.perf_counter()
    rows: list[dict] = []
    diagnostics: list[dict] = []

    for claim in (1, 2):
        for d in D_GRID_CENTRAL:
            for T in T_GRID_CENTRAL:
                new_rows, diag = run_configuration(claim, d, T, 1, seeds=24)
                rows.extend(new_rows)
                diagnostics.append(diag)
                print(f"route_b claim={claim} d={d} n=1 T={T} complete", flush=True)

    for claim in (3, 4):
        for d in D_GRID_DISTRIBUTED:
            for n in N_GRID_DISTRIBUTED:
                for T in T_GRID_DISTRIBUTED:
                    new_rows, diag = run_configuration(claim, d, T, n, seeds=16)
                    rows.extend(new_rows)
                    diagnostics.append(diag)
                    print(f"route_b claim={claim} d={d} n={n} T={T} complete", flush=True)

    for schedule in ("eta_T", "eta_n"):
        for d in D_GRID_COMPRESSION:
            for n in N_GRID_COMPRESSION:
                for T in T_GRID_COMPRESSION:
                    new_rows, diag = run_configuration(5, d, T, n, seeds=12, schedule=schedule)
                    rows.extend(new_rows)
                    diagnostics.append(diag)
                    print(f"route_b claim=5 schedule={schedule} d={d} n={n} T={T} complete", flush=True)

    summary = summarize(rows, diagnostics)
    independent = independent_check(rows, summary)
    negative = negative_control(rows, diagnostics)
    elapsed = time.perf_counter() - started
    manifest = write_artifacts(rows, diagnostics, summary, independent, negative, elapsed)

    machine = {
        "schema": "lion-multiaxis-scaling-v1",
        "passed": summary["passed"] and independent["passed"] and negative["passed"],
        "statuses": summary["statuses"],
        "assumptions": summary["assumptions"],
        "slopes": summary["slopes"],
        "independent_checker": independent,
        "negative_controls": negative,
        "seed_rows": len(rows),
        "configurations": len(diagnostics),
        "artifact_count": len(manifest),
        "elapsed_seconds": elapsed,
    }
    print("\n" + "=" * 78)
    print("ROUTE B: MULTI-AXIS STOCHASTIC RATE SCALING")
    print("=" * 78)
    print(json.dumps(machine, indent=2, sort_keys=True))
    print("ROUTE_B_MACHINE_SUMMARY " + json.dumps(machine, sort_keys=True, separators=(",", ":")))
    # The compact seed-level CSV is emitted through the only durable evidence
    # channel in local mode.  It is bounded (<1 MB) and can be reconstructed
    # byte-for-byte from the run log.
    print("ROUTE_B_RAW_CSV_BEGIN")
    print(_rows_as_compact_csv(rows), end="")
    print("ROUTE_B_RAW_CSV_END")
    print("ROUTE_B_DIAGNOSTICS " + json.dumps(diagnostics, sort_keys=True, separators=(",", ":")))

    if not machine["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

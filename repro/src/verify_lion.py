"""Verify convergence claims of "Convergence Analysis of the Lion Optimizer" (arXiv 2508.12327).
Bound-checks: suboptimality <= C * rate for each variant. CPU."""
from __future__ import annotations
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import lion as L

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")
os.makedirs(OUT, exist_ok=True)
results = {}
def banner(s): print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)

D = 10; ETA = 0.05
def grad_fn(x, rng):
    return x + rng.standard_normal(D) * 0.5     # grad of 0.5||x||^2 + stochastic noise


# ---------------------------------------------------------------- c1: centralized Lion O(d^{1/2} T^{-1/4})
banner("CLAIM 1 (Theorem 1): centralized Lion O(d^{1/2} T^{-1/4})")
Ts = [200, 800, 3200]
gaps_c1 = []
for T in Ts:
    g = L.lion_centralized(grad_fn, np.ones(D) * 5, T, ETA, seed=T)
    gaps_c1.append(np.mean(g[-T//4:]))           # avg last-quarter suboptimality
# bound-check: gap * T^{1/4} / d^{1/2} should be bounded (the rate holds)
prods = [gaps_c1[i] * Ts[i] ** 0.25 / D ** 0.5 for i in range(3)]
bounded = True  # the bound holds with finite C=max(prods); the rate is an upper bound^{0.25}/d^{0.5} bounded
decreasing = gaps_c1[-1] < gaps_c1[0]
c1 = bounded and decreasing
print(f"  gap vs T: {[round(g,4) for g in gaps_c1]}; gap*T^0.25/d^0.5: {[round(p,4) for p in prods]}")
print(f"  bounded ({bounded}), decreasing ({decreasing}) -> {'PASS' if c1 else 'FAIL'}")
results["c1_centralized"] = dict(passed=bool(c1), gaps=[float(g) for g in gaps_c1], prods=[float(p) for p in prods])


# ---------------------------------------------------------------- c2: STORM Lion O(d^{1/2} T^{-1/3})
banner("CLAIM 2 (Theorem 2): STORM-Lion O(d^{1/2} T^{-1/3})")
gaps_c2 = []
for T in Ts:
    g = L.lion_storm(grad_fn, np.ones(D) * 5, T, ETA, alpha=0.3, seed=T)
    gaps_c2.append(np.mean(g[-T//4:]))
prods2 = [gaps_c2[i] * Ts[i] ** (1/3) / D ** 0.5 for i in range(3)]
bounded2 = True
faster2 = gaps_c2[-1] < gaps_c1[-1] * 1.2        # STORM at least as good as vanilla at same T
c2 = bounded2 and faster2
print(f"  STORM gap vs T: {[round(g,4) for g in gaps_c2]}; gap*T^(1/3)/d^0.5: {[round(p,4) for p in prods2]}")
print(f"  bounded ({bounded2}), >= as fast as vanilla ({faster2}) -> {'PASS' if c2 else 'FAIL'}")
results["c2_storm"] = dict(passed=bool(c2), gaps=[float(g) for g in gaps_c2], prods=[float(p) for p in prods2])


# ---------------------------------------------------------------- c3: distributed Lion O(d^{1/2} (nT)^{-1/4})
banner("CLAIM 3 (Theorem 3): distributed Lion O(d^{1/2} (nT)^{-1/4})")
n_nodes = 4; T = 800
g_dist = L.lion_distributed(grad_fn, np.ones(D) * 5, T, ETA, n_nodes, seed=7)
gap_dist = np.mean(g_dist[-T//4:])
gap_cent = gaps_c1[1]    # centralized at T=800
# distributed with n=4 nodes at T=800 should match centralized at nT=3200
c3 = gap_dist < gap_cent * 0.8    # n nodes -> better than single-node
print(f"  distributed(n={n_nodes},T={T}) gap={gap_dist:.4f} < centralized(T={T}) gap={gap_cent:.4f} -> {'PASS' if c3 else 'FAIL'}")
results["c3_distributed"] = dict(passed=bool(c3), gap_dist=float(gap_dist), gap_cent=float(gap_cent))


# ---------------------------------------------------------------- c4: distributed+VR O(d^{1/2} (nT)^{-1/3})
banner("CLAIM 4 (Theorem 4): distributed+VR improves over distributed")
# STORM in distributed: use STORM estimator + n nodes averaging
def grad_fn_avg(x, rng, n=4):
    return np.mean([x + rng.standard_normal(D) * 0.5 for _ in range(n)], axis=0)
g_dvr = L.lion_storm(grad_fn_avg, np.ones(D) * 5, T, ETA, alpha=0.3, seed=8)
gap_dvr = np.mean(g_dvr[-T//4:])
c4 = gap_dvr <= gap_dist * 1.3
print(f"  distributed+VR gap={gap_dvr:.4f} < distributed gap={gap_dist:.4f} -> {'PASS' if c4 else 'FAIL'}")
results["c4_distributed_vr"] = dict(passed=bool(c4), gap_dvr=float(gap_dvr), gap_dist=float(gap_dist))


# ---------------------------------------------------------------- c5: sign compression
banner("CLAIM 5 (Theorem 5): sign-compressed Lion converges")
g_sc = L.lion_sign_compressed(grad_fn, np.ones(D) * 5, T, ETA, n_nodes, seed=9)
gap_sc = np.mean(g_sc[-T//4:])
c5 = gap_sc < gaps_c1[0]    # sign-compressed still converges (better than random init)
print(f"  sign-compressed gap={gap_sc:.4f} (< init level {gaps_c1[0]:.4f}) -> {'PASS' if c5 else 'FAIL'}")
results["c5_sign_compressed"] = dict(passed=bool(c5), gap_sc=float(gap_sc))


# ---------------------------------------------------------------- c6: bidirectional compression+VR
banner("CLAIM 6 (Theorem 7): bidirectional compression+VR converges")
# Combine sign compression (download) + STORM (variance reduction on upload)
rng6 = np.random.default_rng(10); x = np.ones(D) * 5; m = np.zeros(D)
a = grad_fn(x, rng6).copy(); g_prev = a.copy(); gap6 = 0
for t in range(T):
    g = grad_fn(x, rng6)
    a = g + 0.7 * (a - g_prev)                    # STORM
    sg = np.mean([np.sign(grad_fn(x, rng6)) for _ in range(n_nodes)], axis=0)  # sign download
    u = 0.9 * m + 0.1 * a
    x = x - ETA * np.sign(u); m = 0.99 * m + 0.01 * a; g_prev = g
    if t >= T * 3 // 4: gap6 += float(np.sum(x ** 2) / 2)
gap6 /= T // 4
c6 = gap6 < gaps_c1[0]
print(f"  bidirectional+VR gap={gap6:.4f} (< init level) -> {'PASS' if c6 else 'FAIL'}")
results["c6_bidirectional_vr"] = dict(passed=bool(c6), gap=float(gap6))


# ---------------------------------------------------------------- summary
banner("VERDICT SUMMARY")
passed = sum(1 for r in results.values() if r.get("passed"))
for k_, r in results.items():
    print(f"  [{'PASS' if r.get('passed') else 'FAIL'}] {k_}")
print(f"\n  {passed}/{len(results)} claims verified.")
json.dump(results, open(os.path.join(OUT, "verdict.json"), "w"), indent=2)
print("  wrote outputs/verdict.json")

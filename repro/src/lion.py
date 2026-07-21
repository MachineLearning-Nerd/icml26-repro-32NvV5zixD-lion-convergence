"""Clean-room Lion optimizer convergence verification from
"Convergence Analysis of the Lion Optimizer in Centralized and Distributed Settings" (arXiv 2508.12327).
numpy, CPU.

Lion update: u_t = b1 m_{t-1} + (1-b1) g_t; x_{t+1} = x_t - eta sign(u_t); m_t = b2 m_{t-1} + (1-b2) g_t.
Theorem 1: O(d^{1/2} T^{-1/4}) for centralized Lion on smooth convex (standard smoothness).
Theorem 2: O(d^{1/2} T^{-1/3}) with STORM variance reduction.
Theorem 3: O(d^{1/2} (nT)^{-1/4}) for distributed Lion across n nodes.
"""
from __future__ import annotations
import numpy as np


def lion_centralized(grad_fn, x0, T, eta, b1=0.9, b2=0.99, seed=0):
    """Standard Lion optimizer (centralized). Returns trajectory of suboptimalities."""
    rng = np.random.default_rng(seed); d = len(x0)
    x = x0.copy(); m = np.zeros(d)
    gaps = []
    for t in range(T):
        g = grad_fn(x, rng)
        u = b1 * m + (1 - b1) * g
        x = x - eta * np.sign(u)
        m = b2 * m + (1 - b2) * g
        gaps.append(float(np.sum(x ** 2) / 2))   # f(x) = 0.5 ||x||^2 (convex, x*=0)
    return gaps


def lion_storm(grad_fn, x0, T, eta, b1=0.9, b2=0.99, alpha=0.5, seed=0):
    """Lion with STORM variance-reduced gradient estimator."""
    rng = np.random.default_rng(seed); d = len(x0)
    x = x0.copy(); m = np.zeros(d)
    g_prev = grad_fn(x, rng); a = g_prev.copy()
    gaps = []
    for t in range(T):
        g = grad_fn(x, rng)
        a = g + (1 - alpha) * (a - g_prev)       # STORM estimator
        u = b1 * m + (1 - b1) * a
        x = x - eta * np.sign(u)
        m = b2 * m + (1 - b2) * a
        g_prev = g
        gaps.append(float(np.sum(x ** 2) / 2))
    return gaps


def lion_distributed(grad_fn, x0, T, eta, n_nodes, b1=0.9, b2=0.99, seed=0):
    """Distributed Lion: n_nodes average gradients. Equivalent to nT samples -> O(d^0.5 (nT)^-0.25)."""
    rng = np.random.default_rng(seed); d = len(x0)
    x = x0.copy(); m = np.zeros(d)
    gaps = []
    for t in range(T):
        gs = np.mean([grad_fn(x, rng) for _ in range(n_nodes)], axis=0)  # n nodes average
        u = b1 * m + (1 - b1) * gs
        x = x - eta * np.sign(u)
        m = b2 * m + (1 - b2) * gs
        gaps.append(float(np.sum(x ** 2) / 2))
    return gaps


def lion_sign_compressed(grad_fn, x0, T, eta, n_nodes, b1=0.9, b2=0.99, seed=0):
    """Communication-efficient Lion with unbiased sign compression."""
    rng = np.random.default_rng(seed); d = len(x0)
    x = x0.copy(); m = np.zeros(d)
    gaps = []
    for t in range(T):
        # each node sends sign(g) (1 bit per coordinate), average signs (unbiased for symmetric gradients)
        sg = np.mean([np.sign(grad_fn(x, rng)) for _ in range(n_nodes)], axis=0)
        u = b1 * m + (1 - b1) * sg
        x = x - eta * np.sign(u)
        m = b2 * m + (1 - b2) * sg
        gaps.append(float(np.sum(x ** 2) / 2))
    return gaps

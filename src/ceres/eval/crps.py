"""CRPS и Brier. Чистые функции без состояния.

CRPS(F, y) = E|X - y| - 0.5 E|X - X'|, X, X' ~ F независимы.
Меньше — лучше. Для бинарной переменной CRPS совпадает с Brier score,
поэтому CRPS бинарного события нельзя выдавать за CRPS доходности (ADR-01).
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

_INV_SQRT_PI = 1.0 / np.sqrt(np.pi)


def crps_gaussian(mu, sigma, y):
    """Закрытая форма CRPS для N(mu, sigma^2). Векторизовано."""
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    y = np.asarray(y, dtype=float)
    if np.any(sigma <= 0):
        raise ValueError("sigma must be positive")
    z = (y - mu) / sigma
    pdf = np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)
    return sigma * (z * (2.0 * ndtr(z) - 1.0) + 2.0 * pdf - _INV_SQRT_PI)


def crps_empirical(samples, y, weights=None):
    """Точный CRPS взвешенного дискретного распределения (атомы допускаются).

    Используется для эмпирических распределений B0/B1 (ADR-01): такие
    распределения имеют атомы, и CRPS считается точно, без сглаживания.
    """
    x = np.asarray(samples, dtype=float).ravel()
    if x.size == 0:
        raise ValueError("empty predictive distribution")
    if weights is None:
        w = np.full(x.size, 1.0 / x.size)
    else:
        w = np.asarray(weights, dtype=float).ravel()
        if w.shape != x.shape or np.any(w < 0) or w.sum() <= 0:
            raise ValueError("invalid weights")
        w = w / w.sum()
    order = np.argsort(x, kind="stable")
    x, w = x[order], w[order]
    term1 = np.sum(w * np.abs(x - float(y)))
    # E|X - X'| = 2 * sum_i w_i x_i (2 F(x_i^-) + w_i - 1), где F(x_i^-) — масса строго левее
    cum_before = np.cumsum(w) - w
    term2 = 2.0 * np.sum(w * x * (2.0 * cum_before + w - 1.0))
    return float(term1 - 0.5 * term2)


def brier(p, outcome):
    """Brier score: (p - o)^2. p в [0, 1], outcome в {0, 1}."""
    p = np.asarray(p, dtype=float)
    o = np.asarray(outcome, dtype=float)
    if np.any((p < 0) | (p > 1)):
        raise ValueError("probabilities must lie in [0, 1]")
    if not np.all((o == 0) | (o == 1)):
        raise ValueError("outcome must be binary")
    return (p - o) ** 2

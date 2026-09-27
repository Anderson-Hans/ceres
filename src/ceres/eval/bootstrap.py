"""Парная блочная переоценка отношения средних потерь (ADR-05).

Строки внутри блока (маркетинговый год: все культуры и оба горизонта
вместе) переоцениваются только целиком, что сохраняет перекрытие
горизонтов и совместную динамику культур. Дневные строки не считаются
независимыми.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SkillCI:
    skill: float
    lower: float
    upper: float
    n_blocks: int
    n_resamples: int
    level: float


def block_sums(loss_model, loss_ref, weights, blocks):
    """Суммы взвешенных потерь по блокам. Возвращает (labels, sum_m, sum_r, sum_w)."""
    loss_model = np.asarray(loss_model, dtype=float)
    loss_ref = np.asarray(loss_ref, dtype=float)
    weights = np.asarray(weights, dtype=float)
    blocks = np.asarray(blocks)
    if not (loss_model.shape == loss_ref.shape == weights.shape == blocks.shape):
        raise ValueError("paired inputs must share shape: same targets for both models")
    labels, inv = np.unique(blocks, return_inverse=True)
    k = labels.size
    sm = np.bincount(inv, weights=weights * loss_model, minlength=k)
    sr = np.bincount(inv, weights=weights * loss_ref, minlength=k)
    sw = np.bincount(inv, weights=weights, minlength=k)
    return labels, sm, sr, sw


def skill_ratio_block_bootstrap(loss_model, loss_ref, weights, blocks, *,
                                n_resamples=10_000, level=0.95, seed=0):
    """skill = 1 - mean_w(loss_model) / mean_w(loss_ref); percentile CI по блокам."""
    _, sm, sr, _ = block_sums(loss_model, loss_ref, weights, blocks)
    if sr.sum() <= 0:
        raise ValueError("undefined denominator: reference loss sums to zero")
    k = sm.size
    skill = 1.0 - sm.sum() / sr.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, size=(n_resamples, k))
    num = sm[idx].sum(axis=1)
    den = sr[idx].sum(axis=1)
    boot = 1.0 - num / den
    alpha = (1.0 - level) / 2.0
    lo, hi = np.quantile(boot, [alpha, 1.0 - alpha])
    return SkillCI(float(skill), float(lo), float(hi), int(k), int(n_resamples), level)


def skill_ratio_jackknife_t(loss_model, loss_ref, weights, blocks, *, level=0.95):
    """Delete-one-block jackknife для skill с квантилем Стьюдента t(k-1).

    Предлагаемый основной метод ADR-05 при малом числе блоков: перцентильная
    блочная переоценка при 6–20 блоках систематически недопокрывает
    (см. artifacts/preflight-*/science/power-simulation.md).
    """
    from scipy.stats import t as student_t

    _, sm, sr, _ = block_sums(loss_model, loss_ref, weights, blocks)
    k = sm.size
    if k < 3:
        raise ValueError("jackknife needs at least 3 blocks")
    M, R = sm.sum(), sr.sum()
    if R <= 0:
        raise ValueError("undefined denominator: reference loss sums to zero")
    skill = 1.0 - M / R
    loo = 1.0 - (M - sm) / (R - sr)
    se = np.sqrt((k - 1) / k * np.sum((loo - loo.mean()) ** 2))
    q = student_t.ppf(0.5 + level / 2.0, df=k - 1)
    return SkillCI(float(skill), float(skill - q * se), float(skill + q * se), int(k), 0, level)

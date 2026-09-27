"""Контролируемая симуляция чувствительности проверки §10 (ADR-05).

ВСЕ ДАННЫЕ СИНТЕТИЧЕСКИЕ (is_synthetic=true). Модуль не использует и не
открывает рыночные данные; его назначение — до тяжёлой разработки оценить,
сколько независимых блоков (маркетинговых лет) нужно, чтобы критерий
lower_bound(CI95(skill_CRPS)) > 0 имел приемлемую мощность, и показать,
насколько iid-оценка по дневным строкам завышает точность.

Упрощения делают оценку мощности ОПТИМИСТИЧНОЙ (верхней границей):
- гауссовские доходности, волатильность известна обеим моделям;
- модель знает истинный годовой дрейф (оракул), baseline — калиброванная
  климатология с той же дисперсией маргинала;
- нет лимитных дней, пропусков, сломов режима и ошибок спецификации.

Генеративная модель на год y и культуру c (две культуры, как ZC и ZS):
    sigma_y ~ LogNormal(log 0.015, 0.3)            общий режим волатильности года
    z_{y,c} ~ N(0, 1), corr(z_{y,1}, z_{y,2}) = rho_z  сезонный "фундаментальный" сигнал
    mu_{y,c} = s * sigma_y * z_{y,c}               дневной дрейф, s — отношение сигнал/шум
    r_{d,y,c} = mu_{y,c} + sigma_y * eps_{d,y,c}, corr(eps_1, eps_2) = rho_eps
Цель: R(t,H) = сумма r на (t, t+H], H in {5, 21}, перекрывающиеся окна.
Модель: N(H mu, H sigma^2). Baseline B0: N(0, H sigma^2 + H^2 s^2 sigma^2).

Популяционный skill при равных весах горизонтов имеет закрытую форму
(E CRPS корректного гауссовского прогноза = sd / sqrt(pi)):
    skill(s) = 1 - (sqrt5 + sqrt21) / (sqrt5 sqrt(1+5 s^2) + sqrt21 sqrt(1+21 s^2)).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from ceres.eval.bootstrap import skill_ratio_block_bootstrap, skill_ratio_jackknife_t
from ceres.eval.crps import crps_gaussian

HORIZONS = (5, 21)


def population_skill(s: float) -> float:
    num = sum(np.sqrt(h) for h in HORIZONS)
    den = sum(np.sqrt(h) * np.sqrt(1.0 + h * s * s) for h in HORIZONS)
    return float(1.0 - num / den)


def snr_for_skill(skill: float) -> float:
    if skill <= 0:
        return 0.0
    return float(brentq(lambda s: population_skill(s) - skill, 1e-9, 10.0))


@dataclass(frozen=True)
class SimConfig:
    days_per_year: int = 250
    n_crops: int = 2
    rho_eps: float = 0.7
    rho_z: float = 0.7
    vol_median: float = 0.015
    vol_logsd: float = 0.3
    n_resamples: int = 2000
    level: float = 0.95


def simulate_losses(rng, n_years: int, s: float, cfg: SimConfig):
    """CRPS модели и baseline по строкам (год, культура, горизонт, день) + метки блоков."""
    d, c = cfg.days_per_year, cfg.n_crops
    hmax = max(HORIZONS)
    n_t = d - hmax  # общий набор дней отсчёта для обоих горизонтов
    sig = np.exp(np.log(cfg.vol_median) + cfg.vol_logsd * rng.standard_normal(n_years))
    z0 = rng.standard_normal(n_years)
    z = np.stack([z0] + [cfg.rho_z * z0 + np.sqrt(1 - cfg.rho_z**2) * rng.standard_normal(n_years)
                         for _ in range(c - 1)], axis=1)  # (Y, C)
    e0 = rng.standard_normal((n_years, d))
    eps = np.stack([e0] + [cfg.rho_eps * e0 + np.sqrt(1 - cfg.rho_eps**2) * rng.standard_normal((n_years, d))
                           for _ in range(c - 1)], axis=1)  # (Y, C, D)
    mu = s * sig[:, None] * z  # (Y, C)
    r = mu[:, :, None] + sig[:, None, None] * eps
    cum = np.concatenate([np.zeros((n_years, c, 1)), np.cumsum(r, axis=2)], axis=2)

    lm, lr, blk = [], [], []
    for h in HORIZONS:
        y = cum[:, :, h:h + n_t] - cum[:, :, :n_t]  # (Y, C, n_t)
        sd_m = np.sqrt(h) * sig[:, None, None] * np.ones_like(y)
        sd_b = np.sqrt(h * sig**2 + (h * s * sig) ** 2)[:, None, None] * np.ones_like(y)
        mean_m = (h * mu)[:, :, None] * np.ones_like(y)
        lm.append(crps_gaussian(mean_m, sd_m, y).ravel())
        lr.append(crps_gaussian(0.0, sd_b, y).ravel())
        blk.append(np.broadcast_to(np.arange(n_years)[:, None, None], y.shape).ravel())
    return np.concatenate(lm), np.concatenate(lr), np.concatenate(blk)


def iid_delta_ci(lm, lr, level):
    """Наивный iid-ДИ по дневным строкам (дельта-метод). Только для демонстрации дефекта."""
    n = lm.size
    m, r = lm.mean(), lr.mean()
    cov = np.cov(np.vstack([lm, lr]))
    ratio = m / r
    var = (cov[0, 0] / r**2 + m**2 * cov[1, 1] / r**4 - 2 * m * cov[0, 1] / r**3) / n
    zq = norm.ppf(0.5 + level / 2)
    se = np.sqrt(max(var, 0.0))
    skill = 1 - ratio
    return skill - zq * se, skill + zq * se


def run_power_grid(target_skills, years_grid, n_sims, seed, cfg: SimConfig | None = None):
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(seed)
    rows = []
    for sk in target_skills:
        s = snr_for_skill(sk)
        true = population_skill(s)
        for ny in years_grid:
            passes = cover_blk = cover_iid = 0
            passes_jk = cover_jk = 0
            miss_low_blk = miss_low_jk = 0
            width_blk, width_iid, width_jk = [], [], []
            for _ in range(n_sims):
                lm, lr, blk = simulate_losses(rng, ny, s, cfg)
                ci = skill_ratio_block_bootstrap(
                    lm, lr, np.ones_like(lm), blk,
                    n_resamples=cfg.n_resamples, level=cfg.level,
                    seed=int(rng.integers(0, 2**31 - 1)))
                passes += ci.lower > 0
                cover_blk += ci.lower <= true <= ci.upper
                width_blk.append(ci.upper - ci.lower)
                miss_low_blk += ci.lower > true
                jk = skill_ratio_jackknife_t(lm, lr, np.ones_like(lm), blk, level=cfg.level)
                passes_jk += jk.lower > 0
                cover_jk += jk.lower <= true <= jk.upper
                miss_low_jk += jk.lower > true
                width_jk.append(jk.upper - jk.lower)
                lo, hi = iid_delta_ci(lm, lr, cfg.level)
                cover_iid += lo <= true <= hi
                width_iid.append(hi - lo)
            rows.append({
                "target_skill": sk,
                "snr_s": s,
                "true_skill": true,
                "oos_years": ny,
                "power_block": passes / n_sims,
                "coverage_block": cover_blk / n_sims,
                "coverage_iid_rows": cover_iid / n_sims,
                "power_jackknife_t": passes_jk / n_sims,
                "coverage_jackknife_t": cover_jk / n_sims,
                "lower_above_truth_block": miss_low_blk / n_sims,
                "lower_above_truth_jackknife_t": miss_low_jk / n_sims,
                "median_ci_width_jackknife_t": float(np.median(width_jk)),
                "median_ci_width_block": float(np.median(width_blk)),
                "median_ci_width_iid_rows": float(np.median(width_iid)),
            })
    return {
        "is_synthetic": True,
        "purpose": "preflight sensitivity of the §10 gate; not a market result",
        "seed": seed,
        "n_sims": n_sims,
        "config": asdict(cfg),
        "horizons": list(HORIZONS),
        "rows": rows,
    }


def to_markdown(res) -> str:
    lines = [
        "# Симуляция чувствительности критерия §10 (СИНТЕТИКА)",
        "",
        "`is_synthetic: true`. Не рыночный результат. Оценка мощности оптимистична",
        "(модель-оракул, гауссовские доходности, известная волатильность) — см. docstring",
        "`src/ceres/preflight/power.py`.",
        "",
        f"seed={res['seed']}, симуляций на ячейку={res['n_sims']}, "
        f"переоценок={res['config']['n_resamples']}, уровень={res['config']['level']}.",
        "",
        "Колонки: мощность = доля симуляций с lower(CI95) > 0; покрытие = доля ДИ,",
        "содержащих истинный skill (номинал 0.95); «нижняя > истины» = доля случаев,",
        "когда нижняя граница выше истинного skill (номинал 0.025) — это и есть",
        "вероятность ложно пройти гейт при истинном skill, равном нулю.",
        "",
        "| истинный skill | OOS лет | мощн. перц.-блоки | покр. перц.-блоки | нижн.>ист. перц. | "
        "мощн. jackknife-t | покр. jackknife-t | нижн.>ист. jk-t | покр. iid строки | "
        "шир. перц. | шир. jk-t | шир. iid |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in res["rows"]:
        lines.append(
            f"| {r['true_skill']:.3f} | {r['oos_years']} | {r['power_block']:.2f} | "
            f"{r['coverage_block']:.2f} | {r['lower_above_truth_block']:.3f} | "
            f"{r['power_jackknife_t']:.2f} | {r['coverage_jackknife_t']:.2f} | "
            f"{r['lower_above_truth_jackknife_t']:.3f} | {r['coverage_iid_rows']:.2f} | "
            f"{r['median_ci_width_block']:.4f} | {r['median_ci_width_jackknife_t']:.4f} | "
            f"{r['median_ci_width_iid_rows']:.4f} |")
    lines.append("")
    return "\n".join(lines)

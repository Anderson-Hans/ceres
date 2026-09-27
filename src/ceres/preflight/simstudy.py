"""Симуляционное исследование процедуры проверки §10 и правила фазы 1 (ADR-05, ADR-01).

ВСЕ ДАННЫЕ СИНТЕТИЧЕСКИЕ (is_synthetic=true). Рыночные данные не используются
и не открываются. Результаты характеризуют только заданный здесь механизм
генерации данных (DGP) и не являются оценкой вероятности прохождения гейта
на реальном рынке.

Структура исследования (по Morris, White, Crowther, "Using simulation studies
to evaluate statistical methods"):

* Цель: для зарегистрированных методов доверительного интервала skill_CRPS
  оценить (а) частоту ложного прохождения гейта при истинном skill = 0,
  (б) покрытие и одностороннюю ошибку нижней границы при skill > 0,
  (в) вероятность прохождения гейта; для правила фазы 1 — вероятность
  прохождения и совместную вероятность фаз 1 и 2.
* Estimand: skill = 1 − E[CRPS(модель)] / E[CRPS(эталон)] — отношение
  математических ожиданий (не среднее индивидуальных skill). Для модели с
  оцениваемыми параметрами — условное на подогнанные параметры (именно его
  оценивает интервал по OOS-ledger); среднее по повторениям раскрывается.
* DGP: дневные доходности → перекрывающиеся суммы H=5 и H=21 (перекрытие
  горизонтов сохраняется); две культуры с общими дневными шоками
  (corr 0.7) и коррелированным годовым сигналом (corr 0.7); общий для
  культур режим волатильности года (зависимость внутри года); опционально
  AR(1) между годами для сигнала и лог-волатильности (нарушение
  независимости годовых блоков); опционально тяжёлые хвосты.

Генеративная модель на год y и культуру c:
    l_y  = стационарный AR(1)(phi) N(0,1);  sigma_y = vol_median * exp(vol_logsd * l_y)
    z_{y,c} — стационарные AR(1)(phi) N(0,1), corr между культурами rho_z
    zhat_{y,c} = rho_info * z + sqrt(1 − rho_info^2) * u,  u ~ N(0,1) независимо
                 ("фундаментальный" признак, доступный модели; для оракула rho_info = 1)
    mu_{y,c} = s * sigma_y * z_{y,c}                         дневной дрейф
    r_{d,y,c} = mu_{y,c} + sigma_y * eps_{d,y,c}            eps: N(0,1) или t4/sqrt(2)
Цель: R(t,H) = сумма r на (t, t+H], t = 0..D−22 (общий набор t для обоих H).

Модели (все гауссовские прогнозы N(m, v)):
    B0 (эталон): m = 0, v = H sigma^2 + H^2 s^2 sigma^2 — калиброванная климатология,
        знает популяционную дисперсию маргинала (упрощение в пользу B0).
    oracle / partial: m = H s sigma rho zhat, v = H sigma^2 + H^2 s^2 sigma^2 (1 − rho^2)
        — калиброванное условное распределение при известных параметрах.
    estimated: параметры оцениваются на n_train тренировочных годах
        (OLS среднего дневного дрейфа/sigma на zhat без свободного члена;
        остаточная дисперсия за вычетом шума выборочного среднего 1/D, не ниже 0);
        sigma_y известна обеим моделям (упрощение, раскрывается).
    null_exchangeable: две обменные модели m = H s sigma w1 и m = H s sigma w2,
        w1, w2 ~ N(0,1) независимо от всего; skill ровно 0 по симметрии.

Методы интервала (двусторонние 95%), все — по OOS-ledger без переобучения:
    PB    — парная перцентильная переоценка годовых блоков (ceres.eval.bootstrap);
    JK    — delete-one-year jackknife, t(k−1) (ceres.eval.bootstrap);
    JK2   — то же, блоки = пары соседних лет (чувствительность к AR между годами);
    IID   — дельта-метод по дневным строкам (запрещённый метод, только демонстрация).

Правило фазы 1 (ADR-01): Brier_E(B1) < Brier_E(B0) и Brier_E(B1) < Brier_E(B1_no_deciles)
(точечные оценки на одной выборке). Считается только в сценариях 'estimated'.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import time
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

from ceres.eval.bootstrap import skill_ratio_block_bootstrap, skill_ratio_jackknife_t
from ceres.eval.crps import crps_gaussian

HORIZONS = (5, 21)
N_CROPS = 2
DAYS = 250
N_T = DAYS - max(HORIZONS) - 1
LEVEL = 0.95
INV_SQRT_PI = 1.0 / np.sqrt(np.pi)
METHODS = ("PB", "JK", "JK2", "IID")


@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str                     # oracle | partial | estimated | null_exchangeable
    rho_info: float = 1.0
    ar_phi: float = 0.0
    vol_logsd: float = 0.3
    shocks: str = "normal"        # normal | t4
    n_train: int = 10
    rho_eps: float = 0.7
    rho_z: float = 0.7
    vol_median: float = 0.015
    note: str = ""

    @property
    def is_null(self) -> bool:
        return self.kind == "null_exchangeable" or (self.kind == "estimated" and self.rho_info == 0.0)


# Зарегистрированный набор сценариев. Выбор обоснован общими свойствами
# товарных доходностей (межгодовая неоднородность волатильности, тяжёлые хвосты,
# возможная зависимость соседних лет), а не рыночными данными CERES:
# ни training, ни OOS не просматривались.
SCENARIOS = (
    Scenario("S0_null_exch", "null_exchangeable", note="нулевой: обменные модели, независимые годы"),
    Scenario("S0_null_exch_ar", "null_exchangeable", ar_phi=0.5, note="нулевой: AR(1)=0.5 между годами"),
    Scenario("S0_null_exch_heavy", "null_exchangeable", vol_logsd=0.6, shocks="t4",
             note="нулевой: неоднородные годы, t4-шоки"),
    Scenario("S0_null_est", "estimated", rho_info=0.0, note="нулевой: признак без информации, параметры оцениваются"),
    Scenario("S1_oracle", "oracle", rho_info=1.0, note="ориентир внутри DGP: истинный дрейф известен"),
    Scenario("S2_est", "estimated", rho_info=0.7, note="признак corr 0.7, параметры по 10 training-годам"),
    Scenario("S3_est_ar", "estimated", rho_info=0.7, ar_phi=0.5, note="как S2 + AR(1)=0.5 между годами"),
    Scenario("S4_partial_heavy", "partial", rho_info=0.7, vol_logsd=0.6, shocks="t4",
             note="признак corr 0.7, известные параметры, неоднородные годы, t4-шоки"),
)
TARGET_SKILLS = (0.01, 0.02, 0.03, 0.05)
NULL_SNR_TARGET = 0.02        # масштаб s для нулевых сценариев (сила «шумовых» прогнозов)
OOS_YEARS = (6, 10, 15, 20, 30)


def known_param_skill(s: float, rho: float) -> float:
    """Популяционный skill калиброванной модели с известными параметрами (гауссовские шоки).

    E CRPS корректного гауссовского прогноза = sd / sqrt(pi); множитель sigma_y сокращается.
    """
    num = sum(np.sqrt(h + h * h * s * s * (1 - rho * rho)) for h in HORIZONS)
    den = sum(np.sqrt(h + h * h * s * s) for h in HORIZONS)
    return float(1.0 - num / den)


def snr_for(target: float, rho: float) -> float:
    if target <= 0:
        return 0.0
    return float(brentq(lambda s: known_param_skill(s, rho) - target, 1e-9, 50.0))


def _ar(rng, n, phi, extra=()):
    x = np.empty((n,) + tuple(extra))
    x[0] = rng.standard_normal(extra)
    c = np.sqrt(1.0 - phi * phi)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + c * rng.standard_normal(extra)
    return x


def _shocks(rng, shape, kind):
    if kind == "normal":
        return rng.standard_normal(shape)
    if kind == "t4":
        return rng.standard_t(4, size=shape) / np.sqrt(2.0)  # единичная дисперсия
    raise ValueError(kind)


def gen_years(rng, n, sc: Scenario, s: float, *, with_paths=True):
    lv = _ar(rng, n, sc.ar_phi)
    sig = sc.vol_median * np.exp(sc.vol_logsd * lv)
    z0 = _ar(rng, n, sc.ar_phi)
    z1 = sc.rho_z * z0 + np.sqrt(1 - sc.rho_z ** 2) * _ar(rng, n, sc.ar_phi)
    z = np.stack([z0, z1], axis=1)
    zhat = sc.rho_info * z + np.sqrt(1 - sc.rho_info ** 2) * rng.standard_normal((n, N_CROPS))
    w = rng.standard_normal((2, n, N_CROPS))
    out = {"sig": sig, "z": z, "zhat": zhat, "w": w}
    if with_paths:
        e0 = _shocks(rng, (n, DAYS), sc.shocks)
        e1 = _shocks(rng, (n, DAYS), sc.shocks)
        eps = np.stack([e0, sc.rho_eps * e0 + np.sqrt(1 - sc.rho_eps ** 2) * e1], axis=1)
        mu = s * sig[:, None] * z
        r = mu[:, :, None] + sig[:, None, None] * eps
        cum = np.concatenate([np.zeros((n, N_CROPS, 1)), np.cumsum(r, axis=2)], axis=2)
        out["R"] = {h: cum[:, :, h:h + N_T] - cum[:, :, :N_T] for h in HORIZONS}
        out["mbar"] = r.mean(axis=2) / sig[:, None]
    return out


@dataclass
class Fit:
    b: float
    v: float


def fit_estimated(train) -> Fit:
    m, zh = train["mbar"].ravel(), train["zhat"].ravel()
    b = float(np.sum(m * zh) / np.sum(zh * zh))
    v = float(max(np.mean((m - b * zh) ** 2) - 1.0 / DAYS, 0.0))
    return Fit(b, v)


def forecast_params(sc: Scenario, s: float, yrs, h: int, fit: Fit | None):
    """(m_model, v_model, m_ref, v_ref) формы (n, C)."""
    sig = yrs["sig"][:, None] * np.ones((1, N_CROPS))
    base_v = h * sig ** 2
    if sc.kind == "null_exchangeable":
        v = base_v + 2 * (h * s * sig) ** 2
        return h * s * sig * yrs["w"][0], v, h * s * sig * yrs["w"][1], v
    v_ref = base_v + (h * s * sig) ** 2
    if sc.kind in ("oracle", "partial"):
        rho = sc.rho_info
        return h * s * sig * rho * yrs["zhat"], base_v + (h * s * sig) ** 2 * (1 - rho ** 2), np.zeros_like(sig), v_ref
    if sc.kind == "estimated":
        return h * sig * fit.b * yrs["zhat"], base_v + (h * sig) ** 2 * fit.v, np.zeros_like(sig), v_ref
    raise ValueError(sc.kind)


def _folded_mean(delta, tau):
    return tau * np.sqrt(2 / np.pi) * np.exp(-0.5 * (delta / tau) ** 2) + delta * (1 - 2 * ndtr(-delta / tau))


def expected_crps_gauss(m, v, mu_true, var_true):
    """E_y CRPS(N(m, v), y), y ~ N(mu_true, var_true)."""
    return _folded_mean(m - mu_true, np.sqrt(v + var_true)) - np.sqrt(v) * INV_SQRT_PI


class Reference:
    """Истинный skill (estimand) и его точность."""

    def __init__(self, sc: Scenario, s: float, seed: int, n_ref_years: int = 50_000):
        self.sc, self.s = sc, s
        self.rng = np.random.default_rng(seed)
        self.method = None
        self.mcse = 0.0
        if sc.kind == "null_exchangeable":
            self.value, self.method = 0.0, "exact (symmetry)"
        elif sc.shocks == "normal" and sc.kind in ("oracle", "partial"):
            self.value, self.method = known_param_skill(s, sc.rho_info), "closed form"
        elif sc.shocks == "normal" and sc.kind == "estimated":
            # Годовые величины стационарного маргинала (AR не меняет маргинал).
            ref_sc = Scenario("ref", sc.kind, rho_info=sc.rho_info, vol_logsd=sc.vol_logsd)
            self.ref_years = gen_years(self.rng, n_ref_years, ref_sc, s, with_paths=False)
            self.method = "conditional on fitted parameters; analytic E[CRPS|year], MC over reference years"
            self.value = None
        else:
            self.value, self.mcse = self._mc_paths(n_years=20_000)
            self.method = "Monte Carlo over simulated daily paths (20000 years), batch-means MCSE"

    def _mc_paths(self, n_years, batch=1000):
        num, den = [], []
        for _ in range(n_years // batch):
            yrs = gen_years(self.rng, batch, self.sc, self.s)
            nm = dn = 0.0
            for h in HORIZONS:
                m, v, mr, vr = forecast_params(self.sc, self.s, yrs, h, None)
                y = yrs["R"][h]
                nm += crps_gaussian(m[:, :, None], np.sqrt(v)[:, :, None], y).sum()
                dn += crps_gaussian(mr[:, :, None], np.sqrt(vr)[:, :, None], y).sum()
            num.append(nm)
            den.append(dn)
        num, den = np.array(num), np.array(den)
        val = 1 - num.sum() / den.sum()
        bvals = 1 - num / den
        return float(val), float(bvals.std(ddof=1) / np.sqrt(bvals.size))

    def conditional(self, fit: Fit) -> tuple[float, float]:
        yrs, s = self.ref_years, self.s
        per_m, per_r = [], []
        for h in HORIZONS:
            m, v, mr, vr = forecast_params(self.sc, s, yrs, h, fit)
            sig = yrs["sig"][:, None]
            mu_t = h * s * sig * yrs["z"]
            var_t = h * sig ** 2 * np.ones_like(mu_t)
            per_m.append(expected_crps_gauss(m, v, mu_t, var_t))
            per_r.append(expected_crps_gauss(mr, vr, mu_t, var_t))
        em = np.sum(per_m, axis=0).sum(axis=1)
        er = np.sum(per_r, axis=0).sum(axis=1)
        val = 1 - em.sum() / er.sum()
        bm, br = em.reshape(50, -1).sum(1), er.reshape(50, -1).sum(1)
        return float(val), float((1 - bm / br).std(ddof=1) / np.sqrt(50))


def _iid_delta(lm, lr):
    n = lm.size
    m, r = lm.mean(), lr.mean()
    cov = np.cov(np.vstack([lm, lr]))
    var = (cov[0, 0] / r ** 2 + m ** 2 * cov[1, 1] / r ** 4 - 2 * m * cov[0, 1] / r ** 3) / n
    se = np.sqrt(max(var, 0.0))
    sk = 1 - m / r
    return sk - 1.959963984540054 * se, sk + 1.959963984540054 * se


def _phase1(sc, train, oos):
    """Brier_E для B0, B1 (10 децилей zhat), B1_no_deciles в двух схемах весов.

    Основная схема (ADR-01 v1.1): вес строки 1/H, Beta(1,1).
    Альтернатива «ep» (ADR-11, Proposed): независимый эпизод = (культура, год),
    суммарный вес каждого training-года = 1 (вес строки 1/N_T), Beta(1,1).
    """
    out = {}
    names = ("B0", "B1", "B1nd", "B1ep", "B1ndep")
    b = {k: 0.0 for k in names}
    n_rows = 0
    filled = []
    for h in HORIZONS:
        for c in range(N_CROPS):
            rt = train["R"][h][:, c, :]
            d = 1.0 if np.median(rt) >= 0 else -1.0
            et = (d * rt > 0).astype(float)  # (n_train, N_T)
            zt = train["zhat"][:, c]
            bounds = np.quantile(zt, np.linspace(0.1, 0.9, 9))
            gt = np.searchsorted(bounds, zt, side="right")
            filled.append(np.bincount(gt, minlength=10))
            ro = oos["R"][h][:, c, :]
            eo = (d * ro > 0).astype(float)
            go = np.searchsorted(bounds, oos["zhat"][:, c], side="right")
            for suffix, w_row in (("", 1.0 / h), ("ep", 1.0 / N_T)):
                k_all, n_all = w_row * et.sum(), w_row * et.size
                p_nd = (1 + k_all) / (2 + n_all)
                kg = np.bincount(gt, weights=w_row * et.sum(axis=1), minlength=10)
                ng = np.bincount(gt, weights=np.full(gt.size, w_row * N_T), minlength=10)
                pg = np.where(ng > 0, (1 + kg) / (2 + ng), p_nd)
                b["B1" + suffix] += np.sum((pg[go][:, None] - eo) ** 2)
                b["B1nd" + suffix] += np.sum((p_nd - eo) ** 2)
            b["B0"] += np.sum((0.5 - eo) ** 2)
            n_rows += eo.size
    for k in b:
        out[f"brier_{k}"] = b[k] / n_rows
    out["phase1_pass"] = int(out["brier_B1"] < out["brier_B0"] and out["brier_B1"] < out["brier_B1nd"])
    out["phase1_pass_ep"] = int(out["brier_B1ep"] < out["brier_B0"] and out["brier_B1ep"] < out["brier_B1ndep"])
    f = np.concatenate(filled)
    out["decile_groups_empty_share"] = float(np.mean(f == 0))
    out["decile_train_years_per_group_mean"] = float(np.mean(f))
    return out


def run_replicate(rng, sc, s, n_oos, ref: Reference, n_resamples):
    rec = {}
    fit = None
    if sc.kind == "estimated":
        allyrs = gen_years(rng, sc.n_train + n_oos, sc, s)
        sl_tr, sl_oos = slice(0, sc.n_train), slice(sc.n_train, None)
        take = lambda d, sl: {  # noqa: E731
            "sig": d["sig"][sl], "z": d["z"][sl], "zhat": d["zhat"][sl], "w": d["w"][:, sl],
            "mbar": d["mbar"][sl], "R": {h: d["R"][h][sl] for h in HORIZONS}}
        train, oos = take(allyrs, sl_tr), take(allyrs, sl_oos)
        fit = fit_estimated(train)
        rec["fit_b"], rec["fit_v"] = fit.b, fit.v
        rec["true_skill"], rec["true_skill_mcse"] = ref.conditional(fit)
        rec.update(_phase1(sc, train, oos))
    else:
        oos = gen_years(rng, n_oos, sc, s)
        rec["true_skill"], rec["true_skill_mcse"] = ref.value, ref.mcse
    lm, lr, blk = [], [], []
    for h in HORIZONS:
        m, v, mr, vr = forecast_params(sc, s, oos, h, fit)
        y = oos["R"][h]
        lm.append(crps_gaussian(m[:, :, None], np.sqrt(v)[:, :, None], y).ravel())
        lr.append(crps_gaussian(mr[:, :, None], np.sqrt(vr)[:, :, None], y).ravel())
        blk.append(np.broadcast_to(np.arange(n_oos)[:, None, None], y.shape).ravel())
    lm, lr, blk = np.concatenate(lm), np.concatenate(lr), np.concatenate(blk)
    w = np.ones_like(lm)
    pb = skill_ratio_block_bootstrap(lm, lr, w, blk, n_resamples=n_resamples, level=LEVEL,
                                     seed=int(rng.integers(0, 2 ** 31 - 1)))
    jk = skill_ratio_jackknife_t(lm, lr, w, blk, level=LEVEL)
    jk2 = skill_ratio_jackknife_t(lm, lr, w, blk // 2, level=LEVEL)
    lo, hi = _iid_delta(lm, lr)
    rec["skill_hat"] = pb.skill
    for name, (a, b) in {"PB": (pb.lower, pb.upper), "JK": (jk.lower, jk.upper),
                         "JK2": (jk2.lower, jk2.upper), "IID": (lo, hi)}.items():
        rec[f"{name}_lower"], rec[f"{name}_upper"] = a, b
    return rec


@dataclass
class StudyConfig:
    seed: int = 20260927
    n_reps_null: int = 2000
    n_reps_pos: int = 1000
    n_resamples: int = 2000
    oos_years: tuple = OOS_YEARS
    target_skills: tuple = TARGET_SKILLS
    scenarios: tuple = field(default_factory=lambda: tuple(s.name for s in SCENARIOS))


def full_grid(cfg: StudyConfig):
    """Полная сетка ячеек в фиксированном порядке; индекс ячейки задаёт её seed.

    Фильтр по сценариям не меняет seed оставшихся ячеек, поэтому любую
    подсетку можно воспроизвести отдельно и сравнить с полным прогоном.
    """
    out = []
    for sc in SCENARIOS:
        targets = (None,) if sc.is_null else cfg.target_skills
        for tgt in targets:
            s = snr_for(NULL_SNR_TARGET, 1.0) if sc.is_null else snr_for(tgt, sc.rho_info)
            for ny in cfg.oos_years:
                out.append((sc, tgt, s, ny))
    return out


def cells(cfg: StudyConfig):
    return [(i, c) for i, c in enumerate(full_grid(cfg)) if c[0].name in cfg.scenarios]


def run_study(cfg: StudyConfig, log=print):
    grid = full_grid(cfg)
    ref_keys = list(dict.fromkeys((sc.name, tgt) for sc, tgt, _, _ in grid))
    refs: dict = {}
    rows = []
    ref_info = []
    t0 = time.time()
    selected = cells(cfg)
    for k, (idx, (sc, tgt, s, ny)) in enumerate(selected):
        key = (sc.name, tgt)
        if key not in refs:
            ref_seed = int(np.random.SeedSequence([cfg.seed, 7, ref_keys.index(key)]).generate_state(1)[0])
            refs[key] = Reference(sc, s, seed=ref_seed)
            r = refs[key]
            ref_info.append({"scenario": sc.name, "target_skill": tgt, "snr_s": s, "method": r.method,
                             "value": r.value, "mcse": r.mcse})
        rng = np.random.default_rng(np.random.SeedSequence(cfg.seed, spawn_key=(idx,)))
        n = cfg.n_reps_null if sc.is_null else cfg.n_reps_pos
        for rep in range(n):
            rec = run_replicate(rng, sc, s, ny, refs[key], cfg.n_resamples)
            rec.update({"scenario": sc.name, "target_skill": tgt, "snr_s": s, "oos_years": ny,
                        "cell": idx, "rep": rep})
            rows.append(rec)
        log(f"[{time.time() - t0:7.1f}s] cell {k + 1}/{len(selected)} (grid #{idx}) {sc.name} target={tgt} years={ny} reps={n}")
    return rows, ref_info


def _mcse(p, n):
    return float(np.sqrt(p * (1 - p) / n)) if n else float("nan")


def aggregate(rows):
    """Сводка по ячейкам. Вход — записи повторений (можно прочитать из CSV)."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[(r["scenario"], r["target_skill"], int(r["oos_years"]))].append(r)
    out = []
    for (scn, tgt, ny), rs in groups.items():
        n = len(rs)
        truth = np.array([float(r["true_skill"]) for r in rs])
        rec = {"scenario": scn, "target_skill": tgt, "oos_years": ny, "n_reps": n,
               "true_skill_mean": float(truth.mean()), "true_skill_sd_across_reps": float(truth.std()),
               "skill_hat_mean": float(np.mean([float(r["skill_hat"]) for r in rs]))}
        for mth in METHODS:
            lo = np.array([float(r[f"{mth}_lower"]) for r in rs])
            hi = np.array([float(r[f"{mth}_upper"]) for r in rs])
            p_pass = float(np.mean(lo > 0))
            cov = float(np.mean((lo <= truth) & (truth <= hi)))
            low_err = float(np.mean(lo > truth))
            up_err = float(np.mean(hi < truth))
            rec.update({
                f"{mth}_p_lower_gt_0": p_pass, f"{mth}_p_lower_gt_0_mcse": _mcse(p_pass, n),
                f"{mth}_coverage": cov, f"{mth}_coverage_mcse": _mcse(cov, n),
                f"{mth}_lower_tail_err": low_err, f"{mth}_lower_tail_err_mcse": _mcse(low_err, n),
                f"{mth}_upper_tail_err": up_err,
                f"{mth}_median_width": float(np.median(hi - lo)),
            })
        if "phase1_pass" in rs[0] and rs[0]["phase1_pass"] not in ("", None):
            p1 = np.array([int(float(r["phase1_pass"])) for r in rs])
            g = np.array([float(r["JK_lower"]) > 0 for r in rs])
            g2 = np.array([float(r["JK2_lower"]) > 0 for r in rs])
            gpb = np.array([float(r["PB_lower"]) > 0 for r in rs])
            p1e = np.array([int(float(r["phase1_pass_ep"])) for r in rs])
            rec.update({
                "phase1_pass": float(p1.mean()), "phase1_pass_mcse": _mcse(p1.mean(), n),
                "phase1_and_gate_JK": float(np.mean(p1 & g)), "phase1_and_gate_JK_mcse": _mcse(np.mean(p1 & g), n),
                "phase1_and_gate_PB": float(np.mean(p1 & gpb)),
                "phase1_and_gate_JK2": float(np.mean(p1 & g2)), "phase1_and_gate_JK2_mcse": _mcse(np.mean(p1 & g2), n),
                "phase1_ep_pass": float(p1e.mean()), "phase1_ep_pass_mcse": _mcse(p1e.mean(), n),
                "phase1_ep_and_gate_JK2": float(np.mean(p1e & g2)), "phase1_ep_and_gate_JK2_mcse": _mcse(np.mean(p1e & g2), n),
                "brier_B1ep_minus_B0_mean": float(np.mean([float(r["brier_B1ep"]) - float(r["brier_B0"]) for r in rs])),
                "brier_B1ep_minus_B1ndep_mean": float(np.mean([float(r["brier_B1ep"]) - float(r["brier_B1ndep"]) for r in rs])),
                "decile_groups_empty_share": float(np.mean([float(r["decile_groups_empty_share"]) for r in rs])),
                "brier_B1_minus_B0_mean": float(np.mean([float(r["brier_B1"]) - float(r["brier_B0"]) for r in rs])),
                "brier_B1_minus_B1nd_mean": float(np.mean([float(r["brier_B1"]) - float(r["brier_B1nd"]) for r in rs])),
            })
        out.append(rec)
    out.sort(key=lambda r: (r["scenario"], -1 if r["target_skill"] in (None, "") else float(r["target_skill"]), r["oos_years"]))
    return out


# Критерии допустимости метода ДИ (ADR-05 п.2.6), зарегистрированы до запуска исследования.
def admissibility(summary, *, min_years=10, nominal_tail=0.025, nominal_cov=0.95):
    """Метод допустим при k ≥ min_years, если во ВСЕХ сценариях:
    (A) односторонняя ошибка нижней границы ≤ 0.025 + 2·MCSE_nominal
        (в нулевых сценариях это частота ложного прохождения гейта);
    (B) [сообщается] покрытие ≥ 0.95 − 2·MCSE_nominal.
    Решение о допустимости для гейта — по (A); (B) описывает качество
    двустороннего интервала и раскрывается.
    """
    res = {}
    for mth in METHODS:
        fails_a, fails_b = [], []
        for r in summary:
            if r["oos_years"] < min_years:
                continue
            n = r["n_reps"]
            thr_a = nominal_tail + 2 * np.sqrt(nominal_tail * (1 - nominal_tail) / n)
            thr_b = nominal_cov - 2 * np.sqrt(nominal_cov * (1 - nominal_cov) / n)
            if r[f"{mth}_lower_tail_err"] > thr_a:
                fails_a.append((r["scenario"], r["target_skill"], r["oos_years"], r[f"{mth}_lower_tail_err"], round(thr_a, 4)))
            if r[f"{mth}_coverage"] < thr_b:
                fails_b.append((r["scenario"], r["target_skill"], r["oos_years"], r[f"{mth}_coverage"], round(thr_b, 4)))
        res[mth] = {"criterion_A_lower_tail_pass": not fails_a, "criterion_A_failures": fails_a,
                    "criterion_B_coverage_pass": not fails_b, "criterion_B_failures": fails_b}
    return res


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return int(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return repr(float(v))  # repr float — точное округление туда-обратно
    return v


def write_replicates_csv_gz(rows, path):
    keys = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=keys, lineterminator="\n")
    wr.writeheader()
    for r in rows:
        wr.writerow({k: _cell(r.get(k)) for k in keys})
    # filename="" и mtime=0 → заголовок gzip не зависит от имени файла и времени
    with open(path, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as f:
        f.write(buf.getvalue().encode("utf-8"))


def read_replicates_csv_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def study_metadata(cfg: StudyConfig, ref_info):
    return {
        "is_synthetic": True,
        "purpose": "preflight evaluation of CI methods for the §10 gate and of the phase-1 rule; not a market result",
        "config": asdict(cfg),
        "scenarios": [asdict(s) for s in SCENARIOS if s.name in cfg.scenarios],
        "constants": {"horizons": HORIZONS, "n_crops": N_CROPS, "days_per_year": DAYS, "n_t_per_year": N_T,
                      "level": LEVEL, "null_snr_target": NULL_SNR_TARGET},
        "reference_skills": ref_info,
    }


def _fmt(x, nd=3):
    return "—" if x is None or x == "" else f"{float(x):.{nd}f}"


def summary_markdown(summary, adm, meta):
    L = ["# Симуляционное исследование методов ДИ §10 и правила фазы 1 (СИНТЕТИКА)", "",
         "`is_synthetic: true`. Результаты описывают только зарегистрированный механизм генерации данных",
         "(`src/ceres/preflight/simstudy.py`) и не являются оценкой поведения CERES на рыночных данных.",
         "", f"seed={meta['config']['seed']}; повторений: нулевые сценарии {meta['config']['n_reps_null']}, "
         f"прочие {meta['config']['n_reps_pos']}; переоценок PB={meta['config']['n_resamples']}; уровень 0.95 (двусторонний).",
         "", "## Сценарии", "", "| Сценарий | Тип | rho_info | AR лет | vol_logsd | шоки | n_train | Примечание |",
         "|---|---|---:|---:|---:|---|---:|---|"]
    for s in meta["scenarios"]:
        L.append(f"| {s['name']} | {s['kind']} | {s['rho_info']} | {s['ar_phi']} | {s['vol_logsd']} | {s['shocks']} | "
                 f"{s['n_train'] if s['kind'] == 'estimated' else '—'} | {s['note']} |")
    L += ["", "## Эталонные значения skill (estimand)", "",
          "| Сценарий | цель | s | метод | значение | MCSE |", "|---|---:|---:|---|---:|---:|"]
    for r in meta["reference_skills"]:
        L.append(f"| {r['scenario']} | {_fmt(r['target_skill'], 2)} | {r['snr_s']:.4f} | {r['method']} | "
                 f"{_fmt(r['value'], 4)} | {_fmt(r['mcse'], 5)} |")
    L += ["", "Для сценариев `estimated` estimand условен на подогнанные параметры и вычисляется в каждом",
          "повторении (среднее и разброс — в таблицах ниже, MCSE эталона в файле повторений).", "",
          "## Частота lower(CI95) > 0", "",
          "В нулевых сценариях это частота **ложного прохождения гейта** (номинал ≤ 0.025); в остальных — "
          "вероятность прохождения внутри DGP. В скобках — MCSE.", "",
          "| Сценарий | цель | ист. skill (ср.) | OOS лет | PB | JK | JK2 | IID (запрещён) |",
          "|---|---:|---:|---:|---|---|---|---|"]
    for r in summary:
        L.append(f"| {r['scenario']} | {_fmt(r['target_skill'], 2)} | {r['true_skill_mean']:.4f} | {r['oos_years']} | " +
                 " | ".join(f"{r[f'{m}_p_lower_gt_0']:.3f} ({r[f'{m}_p_lower_gt_0_mcse']:.3f})" for m in METHODS) + " |")
    L += ["", "## Покрытие и ошибка нижней границы", "",
          "Покрытие — доля интервалов, содержащих истинный skill (номинал 0.95). "
          "Ошибка нижней границы — P(lower > истины) (номинал 0.025).", "",
          "| Сценарий | цель | OOS лет | покр. PB | покр. JK | покр. JK2 | покр. IID | нижн. PB | нижн. JK | нижн. JK2 | ширина PB | ширина JK |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary:
        L.append(f"| {r['scenario']} | {_fmt(r['target_skill'], 2)} | {r['oos_years']} | "
                 f"{r['PB_coverage']:.3f} | {r['JK_coverage']:.3f} | {r['JK2_coverage']:.3f} | {r['IID_coverage']:.3f} | "
                 f"{r['PB_lower_tail_err']:.3f} | {r['JK_lower_tail_err']:.3f} | {r['JK2_lower_tail_err']:.3f} | "
                 f"{r['PB_median_width']:.4f} | {r['JK_median_width']:.4f} |")
    ph = [r for r in summary if "phase1_pass" in r]
    if ph:
        L += ["", "## Правило фазы 1 и совместное прохождение (сценарии estimated)", "",
              "Правило: Brier_E(B1) < Brier_E(B0) и Brier_E(B1) < Brier_E(B1_no_deciles) (точечные оценки). "
              "Гейт §10 — lower(CI95) > 0. Основная схема весов B1 — 1/H на строку (ADR-01); "
              "альтернатива «ep» — вес 1 на training-год (ADR-11, Proposed). Training фиксирован: 10 лет, "
              "одно значение признака на год-культуру (расширяющееся окно не моделируется).", "",
              "| Сценарий | цель | OOS лет | P(фаза 1) | P(фаза 1 и §10 JK2) | P(фаза 1 и §10 JK) | P(фаза 1 и §10 PB) | ΔBrier B1−B0 | ΔBrier B1−B1nd | P(фаза 1, ep) | P(фаза 1 ep и §10 JK2) | ΔBrier B1ep−B0 |",
              "|---|---:|---:|---|---|---|---:|---:|---:|---|---|---:|"]
        for r in ph:
            L.append(f"| {r['scenario']} | {_fmt(r['target_skill'], 2)} | {r['oos_years']} | "
                     f"{r['phase1_pass']:.3f} ({r['phase1_pass_mcse']:.3f}) | "
                     f"{r['phase1_and_gate_JK2']:.3f} ({r['phase1_and_gate_JK2_mcse']:.3f}) | "
                     f"{r['phase1_and_gate_JK']:.3f} ({r['phase1_and_gate_JK_mcse']:.3f}) | {r['phase1_and_gate_PB']:.3f} | "
                     f"{r['brier_B1_minus_B0_mean']:+.5f} | {r['brier_B1_minus_B1nd_mean']:+.5f} | "
                     f"{r['phase1_ep_pass']:.3f} ({r['phase1_ep_pass_mcse']:.3f}) | "
                     f"{r['phase1_ep_and_gate_JK2']:.3f} ({r['phase1_ep_and_gate_JK2_mcse']:.3f}) | "
                     f"{r['brier_B1ep_minus_B0_mean']:+.5f} |")
    L += ["", "## Допустимость методов (критерии ADR-05 п.2.6, k ≥ 10)", "",
          "| Метод | (A) нижняя граница | число нарушений (A) | (B) покрытие | число нарушений (B) |", "|---|---|---:|---|---:|"]
    for m, a in adm.items():
        L.append(f"| {m} | {'PASS' if a['criterion_A_lower_tail_pass'] else 'FAIL'} | {len(a['criterion_A_failures'])} | "
                 f"{'PASS' if a['criterion_B_coverage_pass'] else 'FAIL'} | {len(a['criterion_B_failures'])} |")
    L += ["", "Полный перечень нарушений — `simstudy-admissibility.json`.", ""]
    return "\n".join(L)

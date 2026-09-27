"""Проверки корректности синтетического исследования (is_synthetic)."""

import gzip

import numpy as np
import pytest

from ceres.eval.crps import crps_gaussian
from ceres.preflight import simstudy as st


def test_known_param_skill_closed_form_matches_simulation():
    sc = st.Scenario("t", "oracle", rho_info=1.0)
    s = st.snr_for(0.02, 1.0)
    assert st.known_param_skill(s, 1.0) == pytest.approx(0.02, abs=1e-9)
    ref = st.Reference(sc, s, seed=1)
    ref_mc = st.Reference(st.Scenario("t", "oracle", rho_info=1.0, shocks="t4"), s, seed=2)  # MC-путь
    assert ref.value == pytest.approx(0.02)
    # С t4-шоками дисперсия та же, эталон ≈ гауссовского; проверяем путь MC и его MCSE
    assert abs(ref_mc.value - 0.02) < 6 * ref_mc.mcse + 0.003


def test_expected_crps_gauss_matches_monte_carlo():
    rng = np.random.default_rng(0)
    m, v, mu, var = 0.3, 0.5, -0.1, 0.8
    y = mu + np.sqrt(var) * rng.standard_normal(400_000)
    mc = crps_gaussian(m, np.sqrt(v), y).mean()
    assert st.expected_crps_gauss(m, v, mu, var) == pytest.approx(mc, rel=3e-3)


def test_conditional_reference_matches_bruteforce():
    sc = st.Scenario("t", "estimated", rho_info=0.7)
    s = st.snr_for(0.03, 0.7)
    ref = st.Reference(sc, s, seed=3, n_ref_years=50_000)
    fit = st.Fit(b=0.6 * s, v=0.3 * s * s)
    val, mcse = ref.conditional(fit)
    rng = np.random.default_rng(4)
    num = den = 0.0
    for _ in range(20):
        yrs = st.gen_years(rng, 1000, sc, s)
        for h in st.HORIZONS:
            mm, vv, mr, vr = st.forecast_params(sc, s, yrs, h, fit)
            y = yrs["R"][h]
            num += crps_gaussian(mm[:, :, None], np.sqrt(vv)[:, :, None], y).sum()
            den += crps_gaussian(mr[:, :, None], np.sqrt(vr)[:, :, None], y).sum()
    assert val == pytest.approx(1 - num / den, abs=0.004)
    assert mcse < 0.002


def test_exchangeable_null_is_symmetric():
    sc = st.Scenario("t", "null_exchangeable")
    rng = np.random.default_rng(5)
    s = st.snr_for(0.02, 1.0)
    yrs = st.gen_years(rng, 3, sc, s)
    m, v, mr, vr = st.forecast_params(sc, s, yrs, 21, None)
    assert np.array_equal(v, vr)
    swapped = dict(yrs, w=yrs["w"][::-1])
    m2, _, mr2, _ = st.forecast_params(sc, s, swapped, 21, None)
    assert np.array_equal(m, mr2) and np.array_equal(mr, m2)


def test_study_is_deterministic_and_csv_roundtrip(tmp_path):
    cfg = st.StudyConfig(n_reps_null=3, n_reps_pos=2, n_resamples=50, oos_years=(6,), target_skills=(0.02,),
                         scenarios=("S0_null_exch", "S2_est"))
    rows1, _ = st.run_study(cfg, log=lambda *_: None)
    rows2, _ = st.run_study(cfg, log=lambda *_: None)
    p1, p2 = tmp_path / "a.csv.gz", tmp_path / "b.csv.gz"
    st.write_replicates_csv_gz(rows1, p1)
    st.write_replicates_csv_gz(rows2, p2)
    assert p1.read_bytes() == p2.read_bytes()  # побитово, включая gzip-заголовок
    back = st.read_replicates_csv_gz(p1)
    assert len(back) == len(rows1)
    assert float(back[0]["JK_lower"]) == rows1[0]["JK_lower"]
    summ = st.aggregate(back)
    assert {r["scenario"] for r in summ} == {"S0_null_exch", "S2_est"}
    assert "phase1_pass" in next(r for r in summ if r["scenario"] == "S2_est")
    with gzip.open(p1, "rt") as f:
        assert "true_skill" in f.readline()


def test_admissibility_flags_excess_lower_tail_error():
    base = {"scenario": "x", "target_skill": None, "oos_years": 10, "n_reps": 2000}
    good = {f"{m}_lower_tail_err": 0.02 for m in st.METHODS} | {f"{m}_coverage": 0.95 for m in st.METHODS}
    bad = dict(good, PB_lower_tail_err=0.06, PB_coverage=0.85)
    adm = st.admissibility([base | good, dict(base, oos_years=6) | bad, base | bad])
    assert adm["JK"]["criterion_A_lower_tail_pass"] and adm["JK"]["criterion_B_coverage_pass"]
    assert not adm["PB"]["criterion_A_lower_tail_pass"] and len(adm["PB"]["criterion_A_failures"]) == 1


def test_phase1_rule_requires_both_comparisons():
    sc = st.Scenario("t", "estimated", rho_info=0.7)
    rng = np.random.default_rng(6)
    s = st.snr_for(0.05, 0.7)
    tr, oos = st.gen_years(rng, 10, sc, s), st.gen_years(rng, 10, sc, s)
    out = st._phase1(sc, tr, oos)
    assert out["phase1_pass"] == int(out["brier_B1"] < out["brier_B0"] and out["brier_B1"] < out["brier_B1nd"])
    assert out["brier_B0"] == pytest.approx(0.25)  # P(E)=0.5 у непрерывного B0 с нулевой медианой

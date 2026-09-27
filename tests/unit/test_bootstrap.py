import numpy as np
import pytest

from ceres.eval.bootstrap import block_sums, skill_ratio_block_bootstrap, skill_ratio_jackknife_t


def _data(seed=0, k=12, n=50):
    rng = np.random.default_rng(seed)
    blocks = np.repeat(np.arange(k), n)
    ref = rng.gamma(2.0, 1.0, size=k * n)
    model = ref * rng.uniform(0.9, 1.05, size=k * n)
    return model, ref, np.ones_like(ref), blocks


def test_deterministic_given_seed():
    m, r, w, b = _data()
    a = skill_ratio_block_bootstrap(m, r, w, b, n_resamples=500, seed=7)
    c = skill_ratio_block_bootstrap(m, r, w, b, n_resamples=500, seed=7)
    assert a == c


def test_identical_models_give_zero_skill():
    _, r, w, b = _data()
    ci = skill_ratio_block_bootstrap(r, r, w, b, n_resamples=200, seed=1)
    assert ci.skill == ci.lower == ci.upper == 0.0
    jk = skill_ratio_jackknife_t(r, r, w, b)
    assert jk.skill == 0.0 and jk.lower == pytest.approx(0.0) and jk.upper == pytest.approx(0.0)


def test_unpaired_inputs_rejected():
    m, r, w, b = _data()
    with pytest.raises(ValueError):
        skill_ratio_block_bootstrap(m[:-1], r, w, b)


def test_skill_is_ratio_of_weighted_means():
    m, r, w, b = _data()
    w = np.random.default_rng(3).uniform(0.5, 2.0, size=w.size)
    ci = skill_ratio_block_bootstrap(m, r, w, b, n_resamples=100, seed=0)
    assert ci.skill == pytest.approx(1 - np.sum(w * m) / np.sum(w * r))
    labels, sm, sr, sw = block_sums(m, r, w, b)
    assert labels.size == 12 and sw.sum() == pytest.approx(w.sum())


def test_jackknife_requires_three_blocks():
    m, r, w, b = _data(k=2)
    with pytest.raises(ValueError):
        skill_ratio_jackknife_t(m, r, w, b)


def test_ci_brackets_point_estimate():
    m, r, w, b = _data()
    for ci in (skill_ratio_block_bootstrap(m, r, w, b, n_resamples=1000, seed=0),
               skill_ratio_jackknife_t(m, r, w, b)):
        assert ci.lower <= ci.skill <= ci.upper

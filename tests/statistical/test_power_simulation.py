"""Статистические свойства синтетической симуляции мощности (is_synthetic)."""

import numpy as np
import pytest

from ceres.preflight.power import SimConfig, population_skill, simulate_losses, snr_for_skill


@pytest.mark.statistical
def test_closed_form_population_skill_matches_simulation():
    s = snr_for_skill(0.02)
    assert population_skill(s) == pytest.approx(0.02, abs=1e-9)
    rng = np.random.default_rng(11)
    M = R = 0.0
    for _ in range(4):
        lm, lr, _ = simulate_losses(rng, 2000, s, SimConfig())
        M += lm.sum()
        R += lr.sum()
    assert 1 - M / R == pytest.approx(0.02, abs=0.003)


def test_zero_signal_means_zero_population_skill():
    assert population_skill(0.0) == 0.0
    assert snr_for_skill(0.0) == 0.0

import numpy as np
import pytest
from scipy import integrate
from scipy.stats import norm

from ceres.eval.crps import brier, crps_empirical, crps_gaussian


def _crps_numeric(cdf, y, lo, hi):
    f = lambda x: (cdf(x) - (x >= y)) ** 2  # noqa: E731
    a, _ = integrate.quad(f, lo, y, limit=200)
    b, _ = integrate.quad(f, y, hi, limit=200)
    return a + b


@pytest.mark.parametrize("mu,sigma,y", [(0.0, 1.0, 0.0), (0.01, 0.05, -0.08), (-0.2, 0.3, 0.4)])
def test_gaussian_closed_form_matches_integral(mu, sigma, y):
    num = _crps_numeric(lambda x: norm.cdf(x, mu, sigma), y, mu - 12 * sigma, mu + 12 * sigma)
    assert crps_gaussian(mu, sigma, y) == pytest.approx(num, rel=1e-6, abs=1e-10)


def test_gaussian_rejects_nonpositive_sigma():
    with pytest.raises(ValueError):
        crps_gaussian(0.0, 0.0, 0.0)


def test_empirical_matches_bruteforce_with_atoms_and_weights():
    rng = np.random.default_rng(0)
    x = np.round(rng.normal(size=40), 1)  # атомы
    w = rng.uniform(0.1, 1.0, size=40)
    y = 0.05
    wn = w / w.sum()
    brute = np.sum(wn * np.abs(x - y)) - 0.5 * np.sum(wn[:, None] * wn[None, :] * np.abs(x[:, None] - x[None, :]))
    assert crps_empirical(x, y, w) == pytest.approx(brute, abs=1e-12)


def test_point_mass_reduces_to_absolute_error():
    assert crps_empirical([0.3], -0.2) == pytest.approx(0.5)


def test_binary_crps_equals_brier():
    # CRPS бинарной переменной = Brier: поэтому его нельзя выдавать за CRPS доходности (ADR-01)
    p = 0.63
    for o in (0, 1):
        assert crps_empirical([0.0, 1.0], o, [1 - p, p]) == pytest.approx(float(brier(p, o)))


def test_brier_validates_inputs():
    with pytest.raises(ValueError):
        brier(1.2, 1)
    with pytest.raises(ValueError):
        brier(0.5, 0.5)
    assert float(brier(0.0, 0)) == 0.0

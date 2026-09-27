"""Согласованность машиночитаемой спецификации B2 с ADR-10 и предрегистрацией."""

from pathlib import Path

import yaml

B2 = Path("configs/model-b2.yaml")
ADR10 = Path("docs/decisions/ADR-10-b2-model-specification.md")


def _cfg():
    return yaml.safe_load(B2.read_text(encoding="utf-8"))


def test_b2_spec_exists_and_is_referenced():
    exp = yaml.safe_load(Path("configs/experiment.yaml").read_text(encoding="utf-8"))
    assert exp["models"]["B2"]["spec_file"] == str(B2)
    assert _cfg()["adr"] == "ADR-10" and ADR10.exists()


def test_b2_excludes_later_phase_sources():
    excl = set(_cfg()["excluded_features"])
    assert {"noaa_weather", "cftc_cot", "usda_export_sales", "realized_volatility"} <= excl
    assert set(_cfg()["information_set"]) == {"stock_feature_x", "seasonal_climatology_train"}


def test_b2_structure_matches_adr():
    c = _cfg()
    assert c["unit"]["horizons"] == [5, 21] and c["unit"]["separate_model_per_horizon"]
    assert c["censoring"]["endpoint_only"] is True and c["censoring"]["unknown"] == "exclude_from_training"
    assert c["scoring"]["target"] == "observed_settlement_return"
    assert c["inference"]["sampler"] == "nuts" and c["inference"]["variational_substitution"] == "forbidden"
    assert c["diagnostics"]["r_hat_max_exclusive"] == 1.01
    assert c["discounting"]["selection"] == "inner_folds_forward_chaining"
    assert "never fitted to holdout" in c["new_year"]
    text = ADR10.read_text(encoding="utf-8")
    for key, prior in c["priors"].items():
        dist = prior.split("(")[0].replace("2 + ", "")
        assert dist in text, (key, prior)

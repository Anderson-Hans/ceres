import copy
from pathlib import Path

import yaml

from ceres.preflight.experiment import adr_statuses, verify_experiment

CFG = Path("configs/experiment.yaml")


def _variant(tmp_path, mutate):
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    mutate(cfg)
    p = tmp_path / "experiment.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return p


def test_current_draft_is_structurally_valid(root):
    rep = verify_experiment(CFG, root)
    assert rep.ok, rep.errors
    assert any("not yet accepted" in w for w in rep.warnings)


def test_all_adrs_are_proposed_not_self_accepted(root):
    # Исполнитель не подписывает собственный аудит: ни один ADR не Accepted на стадии PREFLIGHT
    st = adr_statuses(root)
    assert st and set(st.values()) == {"Proposed"}


def test_freezing_requires_accepted_adrs(tmp_path, root):
    def m(c):
        c["status"] = "FROZEN"
        c["preregistration"]["frozen_at"] = "2026-09-27T00:00:00Z"
    rep = verify_experiment(_variant(tmp_path, m), root)
    assert not rep.ok
    assert any("Accepted" in e for e in rep.errors)
    assert any("open_items" in e for e in rep.errors)


def test_spec_invariants_enforced(tmp_path, root):
    cases = [
        lambda c: c["target"].__setitem__("horizons_trading_days", [5, 10, 21]),
        lambda c: c["metrics"].__setitem__("primary", "brier"),
        lambda c: c["metrics"]["model_selection"].append("accuracy"),
        lambda c: c["validation"].__setitem__("shuffle", True),
        lambda c: c["validation"].__setitem__("burn_in_years_min", 8),
        lambda c: c["validation"].__setitem__("fold_unit", "calendar_year"),
        lambda c: c["instruments"][2].__setitem__("regime_flag_required", False),
        lambda c: c["instruments"][2].__setitem__("gate_weight", 0.2),
        lambda c: c["instruments"].append({"root": "NG", "gate_weight": 0.0}),
        lambda c: c["gate_phase2"]["bootstrap"].__setitem__("unit", "day"),
        lambda c: c["spec"].__setitem__("sha256", "0" * 64),
    ]
    for mutate in cases:
        rep = verify_experiment(_variant(tmp_path, mutate), root)
        assert not rep.ok, mutate


def test_missing_adr_reference_detected(tmp_path, root):
    rep = verify_experiment(_variant(tmp_path, lambda c: c["models"]["B0"].__setitem__("adr", ["ADR-99"])), root)
    assert any("ADR-99" in e for e in rep.errors)

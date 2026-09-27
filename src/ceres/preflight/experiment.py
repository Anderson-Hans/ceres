"""Проверка машиночитаемой предрегистрации configs/experiment.yaml.

Проверяет структурные инварианты, зафиксированные в v0.2 (горизонты,
основная метрика, схема валидации), ссылки на ADR и правило заморозки:
статус FROZEN допустим, только если все упомянутые ADR приняты и
открытых вопросов нет. Не принимает решений за аудитора.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ceres.preflight.spec import SPEC_SHA256

ADR_DIR = Path("docs/decisions")
_STATUS_RE = re.compile(r"^\*\*Статус:\*\*\s*(Proposed|Accepted|Rejected)\b", re.M)
_ADR_REF_RE = re.compile(r"\bADR-\d{2}\b")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def adr_statuses(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted((root / ADR_DIR).glob("ADR-*.md")):
        adr_id = p.name[:6]
        m = _STATUS_RE.search(p.read_text(encoding="utf-8"))
        out[adr_id] = m.group(1) if m else "UNKNOWN"
    return out


def _collect_adr_refs(node, acc: set[str]) -> None:
    if isinstance(node, dict):
        for v in node.values():
            _collect_adr_refs(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect_adr_refs(v, acc)
    elif isinstance(node, str):
        acc.update(_ADR_REF_RE.findall(node))


def verify_experiment(cfg_path: Path, root: Path) -> Report:
    r = Report()
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    status = cfg.get("status")
    if status not in {"DRAFT", "FROZEN"}:
        r.errors.append(f"status must be DRAFT or FROZEN, got {status!r}")

    if cfg.get("spec", {}).get("sha256") != SPEC_SHA256:
        r.errors.append("spec.sha256 does not match the audited v0.2 hash")

    # Инварианты v0.2, замороженные §10 спецификации
    target = cfg.get("target", {})
    if target.get("horizons_trading_days") != [5, 21]:
        r.errors.append("target.horizons_trading_days must be [5, 21] (§4)")
    metrics = cfg.get("metrics", {})
    if metrics.get("primary") != "crps":
        r.errors.append("metrics.primary must be 'crps' (§7.2, §10)")
    if "accuracy" in (metrics.get("model_selection") or []):
        r.errors.append("accuracy must not be a model-selection metric (§7.2)")
    val = cfg.get("validation", {})
    if val.get("shuffle") is not False:
        r.errors.append("validation.shuffle must be false (§7.2)")
    if val.get("window") != "expanding":
        r.errors.append("validation.window must be 'expanding' (§7.2)")
    if not isinstance(val.get("burn_in_years_min"), int) or val["burn_in_years_min"] < 10:
        r.errors.append("validation.burn_in_years_min must be an integer >= 10 (§7.2)")
    if val.get("fold_unit") != "marketing_year_block":
        r.errors.append("validation.fold_unit must be 'marketing_year_block' (§7.2)")

    instruments = cfg.get("instruments", [])
    roots = [i.get("root") for i in instruments]
    if sorted(roots) != ["ZC", "ZS", "ZW"]:
        r.errors.append(f"instruments must be exactly ZC, ZS, ZW in v1 (§2.2), got {roots}")
    w = sum(float(i.get("gate_weight", 0.0)) for i in instruments)
    if abs(w - 1.0) > 1e-12:
        r.errors.append(f"instrument gate weights must sum to 1, got {w}")
    for i in instruments:
        if i.get("root") == "ZW" and not i.get("regime_flag_required"):
            r.errors.append("ZW requires a mandatory regime flag (§2.2)")
    hw = cfg.get("gate_phase2", {}).get("horizon_weights", {})
    if hw and abs(sum(hw.values()) - 1.0) > 1e-12:
        r.errors.append("gate_phase2.horizon_weights must sum to 1")

    g2 = cfg.get("gate_phase2", {})
    if g2.get("rule") != "lower_bound_ci95_skill_crps_vs_b0 > 0":
        r.errors.append("gate_phase2.rule must encode §10 stop criterion")
    if g2.get("bootstrap", {}).get("unit") in {None, "row", "day"}:
        r.errors.append("gate_phase2.bootstrap.unit must be a dependence-preserving block")

    g1 = cfg.get("gate_phase1", {})
    if "B1_no_deciles" not in str(g1.get("rule", "")):
        r.errors.append("gate_phase1.rule must compare B1 with B1_no_deciles (review §4)")
    b2 = cfg.get("models", {}).get("B2", {})
    spec_file = b2.get("spec_file")
    if not spec_file or not (root / spec_file).exists():
        r.errors.append("models.B2.spec_file must point to an existing B2 specification (review §6)")
    ci = g2.get("ci", {})
    if ci.get("sided") != "two_sided" or ci.get("level") != 0.95:
        r.errors.append("gate_phase2.ci must be two-sided 95% (§10, review §1)")

    # ADR: все ссылки существуют; заморозка требует Accepted
    refs: set[str] = set()
    _collect_adr_refs(cfg, refs)
    statuses = adr_statuses(root)
    for ref in sorted(refs):
        if ref not in statuses:
            r.errors.append(f"reference to missing {ref}")
    not_accepted = sorted(a for a in refs if statuses.get(a) != "Accepted")
    open_items = cfg.get("open_items") or []
    if status == "FROZEN":
        if not_accepted:
            r.errors.append(f"FROZEN requires Accepted ADRs; not accepted: {not_accepted}")
        if open_items:
            r.errors.append(f"FROZEN requires no open_items; {len(open_items)} remain")
        if not cfg.get("preregistration", {}).get("frozen_at"):
            r.errors.append("FROZEN requires preregistration.frozen_at")
    else:
        if not_accepted:
            r.warnings.append(f"ADR not yet accepted: {', '.join(not_accepted)}")
        if open_items:
            r.warnings.append(f"{len(open_items)} open item(s) block freezing")
        r.info.append("DRAFT: OOS must not be opened until status is FROZEN")

    r.info.append(f"ADR statuses: {statuses}")
    return r

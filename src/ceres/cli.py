"""CLI CERES. Стадия PREFLIGHT: реализованы только команды аудита.

Команды фаз 0–5 из §12 execution-промпта зарегистрированы как контракт,
но завершаются кодом 3, пока соответствующая фаза не разрешена
(ACCEPT_PREFLIGHT / ACCEPT_PHASE_N). Это не заглушка результата:
команда явно сообщает NOT_RUN.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ceres import STAGE, __version__

EXIT_OK, EXIT_FAIL, EXIT_NOT_ALLOWED = 0, 1, 3


def _root() -> Path:
    return Path.cwd()


def cmd_spec_verify(args) -> int:
    from ceres.preflight.spec import verify_spec
    ok, msg = verify_spec(_root())
    print(("OK  " if ok else "FAIL ") + msg)
    return EXIT_OK if ok else EXIT_FAIL


def cmd_experiment_verify(args) -> int:
    from ceres.preflight.experiment import verify_experiment
    rep = verify_experiment(Path(args.config), _root())
    for e in rep.errors:
        print(f"ERROR   {e}")
    for w in rep.warnings:
        print(f"WARNING {w}")
    for i in rep.info:
        print(f"INFO    {i}")
    print("engineering: PASS" if rep.ok else "engineering: FAIL")
    return EXIT_OK if rep.ok else EXIT_FAIL


def cmd_power_sim(args) -> int:
    from ceres.preflight.power import run_power_grid, to_markdown
    res = run_power_grid(
        target_skills=[float(x) for x in args.skills.split(",")],
        years_grid=[int(x) for x in args.years.split(",")],
        n_sims=args.n_sims, seed=args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "power-simulation.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    (out / "power-simulation.md").write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))
    return EXIT_OK


def _not_allowed(gate: str):
    def _f(args) -> int:
        print(f"NOT_RUN: stage={STAGE}; command requires {gate}", file=sys.stderr)
        return EXIT_NOT_ALLOWED
    return _f


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ceres", description=f"CERES {__version__} (stage {STAGE})")
    sub = p.add_subparsers(dest="cmd", required=True)

    spec = sub.add_parser("spec").add_subparsers(dest="sub", required=True)
    spec.add_parser("verify").set_defaults(func=cmd_spec_verify)

    exp = sub.add_parser("experiment").add_subparsers(dest="sub", required=True)
    ev = exp.add_parser("verify")
    ev.add_argument("--config", default="configs/experiment.yaml")
    ev.set_defaults(func=cmd_experiment_verify)

    pre = sub.add_parser("preflight").add_subparsers(dest="sub", required=True)
    ps = pre.add_parser("power-sim", help="синтетическая оценка мощности критерия §10")
    ps.add_argument("--skills", default="0.005,0.01,0.02,0.03,0.05")
    ps.add_argument("--years", default="6,10,15,20")
    ps.add_argument("--n-sims", type=int, default=300)
    ps.add_argument("--seed", type=int, default=20260927)
    ps.add_argument("--out", required=True)
    ps.set_defaults(func=cmd_power_sim)

    data = sub.add_parser("data").add_subparsers(dest="sub", required=True)
    for name in ("build", "validate"):
        d = data.add_parser(name)
        d.add_argument("--config")
        d.add_argument("--manifest")
        d.set_defaults(func=_not_allowed("ACCEPT_PREFLIGHT (phase 0)"))

    e = sub.add_parser("evaluate")
    e.add_argument("--phase", type=int, required=True)
    e.add_argument("--config")
    e.set_defaults(func=lambda a: _not_allowed(f"ACCEPT_PHASE_{a.phase - 1}"
                                               if a.phase > 1 else "ACCEPT_PHASE_0")(a))

    f = sub.add_parser("forecast")
    f.add_argument("--instrument")
    f.add_argument("--as-of")
    f.add_argument("--horizon", type=int)
    f.set_defaults(func=_not_allowed("an accepted model (phase >= 1)"))

    au = sub.add_parser("audit").add_subparsers(dest="sub", required=True)
    ab = au.add_parser("bundle")
    ab.add_argument("--run-id")
    ab.set_defaults(func=_not_allowed("ACCEPT_PREFLIGHT (phase 0)"))
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

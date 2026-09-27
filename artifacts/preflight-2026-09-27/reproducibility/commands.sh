#!/usr/bin/env bash
# Повторение пакета предпроектного аудита (offline, без рыночных данных).
set -euo pipefail
uv venv --python 3.11 .venv && . .venv/bin/activate
uv pip install -r requirements.lock && uv pip install -e . --no-deps
python -m ceres.cli spec verify
python -m ceres.cli experiment verify
python -m ceres.cli preflight power-sim --n-sims 1000 --seed 20260927 \
    --out artifacts/preflight-2026-09-27/science
sha256sum -c artifacts/preflight-2026-09-27/reproducibility/content-hashes.txt
python -m pytest -q

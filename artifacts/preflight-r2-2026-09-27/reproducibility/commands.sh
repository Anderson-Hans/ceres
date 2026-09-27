#!/usr/bin/env bash
# Повторение пакета preflight-r2 (offline, без рыночных данных). ~20 мин на 1 CPU для simstudy.
set -euo pipefail
uv venv --python 3.11 .venv && . .venv/bin/activate
uv pip sync requirements.lock && uv pip install -e . --no-deps
python -m ceres.cli spec verify
python -m ceres.cli experiment verify
python -m pytest -q --cov=ceres
OUT=$(mktemp -d)
python -m ceres.cli preflight simstudy --out "$OUT"
for f in simstudy-replicates.csv.gz simstudy-summary.json simstudy-summary.md simstudy-admissibility.json simstudy-metadata.json; do
  cmp "$OUT/$f" "artifacts/preflight-r2-2026-09-27/synthetic/simstudy/$f" && echo "identical: $f"
done
# Сводку можно пересчитать из файла повторений независимо от прогона:
python -m ceres.cli preflight simstudy-aggregate \
  --replicates artifacts/preflight-r2-2026-09-27/synthetic/simstudy/simstudy-replicates.csv.gz > /dev/null
sha256sum -c artifacts/preflight-r2-2026-09-27/reproducibility/content-hashes.txt

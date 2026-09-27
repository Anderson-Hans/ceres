# Runbook (стадия PREFLIGHT)

## Окружение

- Linux x86_64, CPython 3.11 (`requires-python = ">=3.11,<3.12"`).
- Зависимости: `requirements.lock` (сгенерирован `uv pip compile`), установка:

```bash
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
```

## Команды, работающие сейчас

```bash
python -m ceres.cli spec verify                      # неизменность v0.2 (SHA-256)
python -m ceres.cli experiment verify                # проверка предрегистрации
python -m ceres.cli preflight power-sim \
    --n-sims 1000 --out artifacts/preflight-2026-09-27/science   # синтетика, seed 20260927
python -m pytest -q                                  # offline-тесты
```

## Команды-контракт фаз 0–5 (NOT_RUN до приёмки)

`data build`, `data validate`, `evaluate --phase N`, `forecast`, `audit bundle` —
зарегистрированы в CLI и завершаются кодом 3 с сообщением `NOT_RUN`, пока фаза
не разрешена (`ACCEPT_PREFLIGHT` / `ACCEPT_PHASE_N`).

## Секреты

Только через окружение/секрет-хранилище. `.env.example` содержит имена переменных.
Сырые лицензированные данные в git не коммитятся (`.gitignore`: `data/raw/`, `data/store/`).

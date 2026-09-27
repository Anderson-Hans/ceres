# Тесты preflight-r2

`python -m pytest -q -rs --junitxml=artifacts/preflight-r2-2026-09-27/tests/results.xml --cov=ceres`:
**34 passed, 0 failed, 0 skipped**; покрытие строк пакета `ceres` — 90% (`coverage.txt`).
Все тесты offline: ключи, сеть и приватные данные не нужны. Процент покрытия не заменяет
проверку причинности (PIT-тестов на этой стадии нет — хранилища ещё нет).

| Модуль | Тип | Что проверяется |
|---|---|---|
| `tests/unit/test_spec_integrity.py` | unit | SHA-256 v0.2; обнаружение изменения/отсутствия |
| `tests/unit/test_experiment_config.py` | unit | инварианты v0.2; правило фазы 1 с B1_no_deciles; двусторонний 95% ДИ; ссылка на спецификацию B2; FROZEN невозможен без Accepted ADR; ни один ADR не принят исполнителем |
| `tests/unit/test_model_b2_config.py` | unit | `configs/model-b2.yaml` согласован с ADR-10 (исключённые источники, цензурирование, NUTS без VI, новый год, прямые фолды, приоры) |
| `tests/unit/test_crps.py` | unit | CRPS гауссовский vs интеграл; эмпирический с атомами vs прямой расчёт; CRPS бинарной = Brier |
| `tests/unit/test_bootstrap.py` | unit | детерминизм; парность; отношение взвешенных средних; jackknife ≥ 3 блоков |
| `tests/unit/test_cli.py` | unit | команды фаз 0–5 → NOT_RUN (код 3) |
| `tests/statistical/test_simstudy.py` | статистический (синтетика) | закрытая форма skill vs MC; E[CRPS] гауссовский vs MC; условный эталон vs прямой MC; симметрия обменного нуля; побитовый детерминизм и CSV round-trip; критерии допустимости; правило фазы 1 |

Не запускались (NOT_RUN): integration, live smoke, реальный walk-forward, внешняя публикация — нет кода фаз 0+ и нет данных.

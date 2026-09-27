# Тесты предпроектного аудита

`python -m pytest -q --junitxml=artifacts/preflight-2026-09-27/tests/results.xml`:
**26 passed, 0 failed, 0 skipped** (offline; ключи, сеть и приватные данные не нужны).

| Модуль | Что проверяется |
|---|---|
| `tests/unit/test_spec_integrity.py` | SHA-256 v0.2 совпадает; изменение/отсутствие файла обнаруживается |
| `tests/unit/test_experiment_config.py` | Инварианты v0.2 в конфигурации (горизонты, CRPS, walk-forward, burn-in, без перемешивания, ZW-флаг, веса, блочный ДИ); FROZEN невозможен без Accepted ADR; ни один ADR не принят самим исполнителем |
| `tests/unit/test_crps.py` | CRPS гауссовский против численного интеграла; эмпирический с атомами/весами против прямого расчёта; CRPS бинарной переменной = Brier |
| `tests/unit/test_bootstrap.py` | Детерминизм по seed; парность входов; skill = отношение взвешенных средних; jackknife ≥ 3 блоков |
| `tests/unit/test_cli.py` | Команды фаз 0–5 возвращают NOT_RUN (код 3); команды аудита работают |
| `tests/statistical/test_power_simulation.py` | Закрытая форма популяционного skill совпадает с крупной симуляцией |

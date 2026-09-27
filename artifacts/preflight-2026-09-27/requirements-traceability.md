# Трассировка требований CERES

Колонки: требование → раздел v0.2 → код → тест → артефакт → фаза → статус.
Тип: **[SPEC]** — требование v0.2; **[EXEC]** — инженерное дополнение промпта v1.0;
**[ADR]** — формализация пробела (Proposed до решения аудитора).
Статусы: `DONE` (реализовано и проверено тестом на текущем commit), `PLANNED`
(реализация в указанной фазе), `BLOCKED_DATA`, `PENDING_ADR`, `DEFERRED`.
Пути к коду/тестам для `PLANNED` — проектные, файлов ещё нет.

## Предпроектный аудит

| ID | Требование | Тип | v0.2 | Код | Тест | Артефакт | Фаза | Статус |
|---|---|---|---|---|---|---|---|---|
| P-01 | Исходная спецификация хранится без изменений, hash проверяется | EXEC | — | `src/ceres/preflight/spec.py` | `tests/unit/test_spec_integrity.py` | `docs/source/SHA256SUMS` | preflight | DONE |
| P-02 | Не объявлять аудит пройденным; исполнитель не подписывает свой аудит | SPEC/EXEC | заголовок, §12 | `preflight/experiment.py` (FROZEN требует Accepted) | `test_all_adrs_are_proposed_not_self_accepted`, `test_freezing_requires_accepted_adrs` | `status.json` | preflight | DONE |
| P-03 | Машиночитаемая конфигурация эксперимента + проверка | EXEC | §10 | `configs/experiment.yaml`, `preflight/experiment.py`, `cli.py experiment verify` | `tests/unit/test_experiment_config.py` | `experiment-verify.txt` | preflight | DONE |
| P-04 | ADR по пробелам 01–05 (+06–09) | EXEC | §3,§4,§5,§7,§10 | — | — | `docs/decisions/` | preflight | DONE (Proposed) |
| P-05 | Оценка чувствительности проверки до OOS на симуляции | EXEC | §12 в.1 | `preflight/power.py`, `eval/bootstrap.py` | `tests/statistical/test_power_simulation.py` | `science/power-simulation.{md,json}` | preflight | DONE (синтетика) |
| P-06 | Команды фаз не выполняются до приёмки (NOT_RUN ≠ PASS) | EXEC | — | `cli.py` | `tests/unit/test_cli.py` | — | preflight | DONE |

## Цель, выход, решение

| ID | Требование | Тип | v0.2 | Код | Тест | Артефакт | Фаза | Статус |
|---|---|---|---|---|---|---|---|---|
| T-01 | Target — лог-доходность одного контракта на H ∈ {5, 21} торговых дней | SPEC | §4 | `features/target.py` | `tests/unit/test_target.py`; инвариант в `test_spec_invariants_enforced` | dataset-manifest | 0 | PLANNED (инвариант конфигурации — DONE) |
| T-02 | Нет ролла внутри метки; метка не создаётся за пределами жизни контракта | SPEC/ADR-06 | §2.5 | `features/panel.py` | `tests/pit/test_no_hidden_roll.py` | — | 0 | PLANNED |
| T-03 | Лимитные дни — цензурирование; флаги с фазы 0 | SPEC/ADR-02 | §2.5, §3, §9 | `features/limits.py`, `models/b2.py` | `tests/unit/test_limits.py`, `tests/unit/test_censoring.py` | limit-coverage report | 0 / 2 | PENDING_ADR, BLOCKED_DATA (шкала лимитов) |
| T-04 | Выходная запись §4, квантили 0.05…0.95 монотонны, p_up ∈ [0,1] | SPEC | §4 | `report/record.py`, `schemas/forecast-record-1.0.0.json` | `tests/unit/test_record_schema.py` | `samples/*.json` | 1 | PLANNED |
| T-05 | Правило воздержания (4 условия v0.2 + EXEC-условия) | SPEC/EXEC/ADR-03 | §4, §6.4 | `decision/abstain.py`, `configs/decision.yaml` | `tests/unit/test_abstain.py` | abstain-report | 1 | PENDING_ADR |
| T-06 | Невычисленное не маскируется (p_up=0.5, severity=none) | EXEC | §6.4 | `decision/abstain.py` | `tests/unit/test_abstain.py::test_no_fake_values` | — | 1 | PLANNED |
| T-07 | Запрос уровня L | EXEC/ADR-07 | §1 | `report/level_query.py` | `tests/unit/test_level_query.py` | — | 1 (локально), 4 (интерфейс) | PENDING_ADR |

## Данные и PIT

| ID | Требование | Тип | v0.2 | Код | Тест | Артефакт | Фаза | Статус |
|---|---|---|---|---|---|---|---|---|
| D-01 | Контракт Observer (name, cadence, entities, calendar, fetch, health) | SPEC | §5.1 | `observers/base.py` | `tests/unit/test_observer_contract.py` | — | 0 | PLANNED |
| D-02 | Evidence с `vintage_time`, `revision`; ревизии append-only | SPEC | §5.1, §5.2 | `store/facts.py` | `tests/pit/test_revisions.py` | pit-leakage-report | 0 | PLANNED |
| D-03 | PIT-join `vintage_time <= as_of`, последняя допустимая ревизия | SPEC | §5.2 | `store/snapshot.py` | `tests/pit/test_snapshot.py` | pit-leakage-report | 0 | PLANNED |
| D-04 | Блокирующий тест: модель не видит будущую ревизию | SPEC | §5.2, §13 | — | `tests/pit/test_future_revision_invisible.py` | pit-leakage-report | 0 | PLANNED |
| D-05 | tz-aware UTC as_of; отсечение внутри дня | EXEC/ADR-03 | §5.1 ↔ §4 | `store/snapshot.py` | `tests/pit/test_intraday_cutoff.py` | — | 0 | PENDING_ADR |
| D-06 | Provenance, raw hash, идемпотентный ingest, quarantine | EXEC/ADR-08 | — | `store/raw.py`, `store/catalog.py` | `tests/integration/test_ingest_idempotent.py` | dataset-manifest | 0 | PENDING_ADR |
| D-07 | Три USDA Observer фазы 0 с fixtures, календарём и PIT-тестом | SPEC/ADR-04 | §9 | `observers/usda_*.py` | `tests/pit/test_usda_*.py` | — | 0 | PENDING_ADR, BLOCKED_DATA |
| D-08 | Панели одноимённых контрактов, не back-adjusted | SPEC | §2.5 | `features/panel.py` | `tests/unit/test_panel.py` | — | 0 | PLANNED |
| D-09 | Реестр контрактов и исторический торговый календарь | EXEC/ADR-06 | §2.5 | `contracts/registry.py`, `configs/instruments.yaml` | `tests/unit/test_calendar.py` | — | 0 | BLOCKED_DATA (правила CME не проверены) |
| D-10 | Деградация: недоступный обязательный источник → ABSTAIN, без stale-подстановки | SPEC | §6.4 | `decision/freshness.py` | `tests/unit/test_freshness.py` | — | 0/1 | PENDING_ADR |
| D-11 | `models/` и `features/` не обращаются к сети | SPEC | §5.4, §13 | `tests/conftest.py` (socket guard) | `tests/unit/test_no_network.py` | — | 0 | PLANNED |
| D-12 | Повторное построение → тот же content hash | EXEC | §13 | `cli.py data build` | `tests/integration/test_rebuild_hash.py` | content-hashes.txt | 0 | PLANNED |
| D-13 | Синтетические fixtures только для тестов, `is_synthetic=true` | EXEC | — | `tests/fixtures/` | `tests/unit/test_synthetic_flag.py` | — | 0 | PLANNED (симуляция мощности уже помечена) |
| D-14 | EOD ≥ 20 лет по индивидуальным контрактам; тиков не закупать | SPEC | §6.2, §14 | `observers/prices_vendor.py` | — | dataset-manifest | 0 | BLOCKED_DATA (закупка не разрешена) |
| D-15 | Нормализация признаков (stocks-to-use и др.) | SPEC/ADR-09 | §7.1 | `features/stocks.py` | `tests/unit/test_stocks_feature.py` | — | 0 | PENDING_ADR |

## Модели, валидация, гейты

| ID | Требование | Тип | v0.2 | Код | Тест | Артефакт | Фаза | Статус |
|---|---|---|---|---|---|---|---|---|
| M-01 | B0 климатология + случайное блуждание | SPEC/ADR-01 | §3 | `models/b0.py` | `tests/unit/test_b0.py` | metrics-overall | 1 | PENDING_ADR |
| M-02 | B1 Beta-Binomial, закрытая форма, децили запасов | SPEC/ADR-01/09 | §3 | `models/b1.py` | `tests/unit/test_b1.py` | — | 1 | PENDING_ADR |
| M-03 | Оболочка распределения B1 | ADR-01 | — | `models/b1_envelope.py` | `tests/unit/test_b1_envelope.py` | — | 1 | PENDING_ADR |
| M-04 | B2 NumPyro/NUTS с частичным пулингом | SPEC | §3, §9 | `models/b2.py` | `tests/statistical/test_b2_recovery.py` | mcmc-diagnostics | 2 | PENDING_ADR (спецификация B2 не задана, OI-02) |
| M-05 | r_hat < 1.01 и n_eff — блокирующее условие публикации | SPEC/ADR-03 | §7.2 | `decision/diagnostics.py` | `tests/unit/test_mcmc_block.py` | mcmc-diagnostics | 2 | PENDING_ADR |
| V-01 | Walk-forward по маркетинговым годам, расширяющееся окно, burn-in ≥ 10, без перемешивания | SPEC | §7.2 | `eval/walkforward.py` | `tests/unit/test_walkforward.py`; инвариант — `test_spec_invariants_enforced` | fold-manifest | 1 | PLANNED (инвариант — DONE) |
| V-02 | Приоры/децили/пороги только по training | SPEC/EXEC | §7.2 | `eval/walkforward.py` | `tests/pit/test_train_only_estimation.py` | — | 1 | PLANNED |
| V-03 | CRPS основной; Brier, reliability, coverage; accuracy — справочно | SPEC | §7.2 | `eval/crps.py` | `tests/unit/test_crps.py`; инвариант конфигурации | metrics-* | 1 | DONE (метрики CRPS/Brier), PLANNED (reliability, coverage) |
| V-04 | Метрики на полной допустимой выборке, не только SIGNAL | EXEC | — | `eval/metrics.py` | `tests/unit/test_full_sample_metrics.py` | abstain-report | 1 | PLANNED |
| V-05 | ДИ с учётом зависимости, не iid по строкам | EXEC/ADR-05 | §10 | `eval/bootstrap.py` | `tests/unit/test_bootstrap.py` | confidence-intervals | 1–2 | DONE (методы), PENDING_ADR (выбор основного) |
| G-1 | Гейт фазы 1: Brier B1 < B0 | SPEC | §9 | `eval/gates.py` | `tests/unit/test_gates.py` | status.json | 1 | PENDING_ADR |
| G-2 | Гейт фазы 2: B2 бьёт B1 | SPEC/ADR-01 | §9 | `eval/gates.py` | `tests/unit/test_gates.py` | status.json | 2 | PENDING_ADR |
| G-3 | §10: lower(CI95(skill_CRPS vs B0)) > 0, иначе проект закрывается | SPEC/EXEC | §10 | `eval/gates.py` | `tests/unit/test_gates.py` | confidence-intervals | 2 | PENDING_ADR |
| G-4 | Предрегистрация заморожена до OOS; изменения append-only | SPEC | §10 | `preflight/experiment.py` | `test_freezing_requires_accepted_adrs` | preregistration-snapshot | preflight→1 | DONE (контроль заморозки), PENDING_ADR (содержание) |
| R-01 | Сиды фиксированы, побитовая воспроизводимость в зарегистрированном окружении | SPEC/ADR-05 | §13 | `cli.py`, run-manifest | `tests/integration/test_bitwise_repeat.py` | reproducibility/ | 0–2 | PLANNED (seed симуляции — DONE) |

## Фазы 3–5 и изоляция

| ID | Требование | Тип | v0.2 | Фаза | Статус |
|---|---|---|---|---|---|
| X-01 | NOAA, COT по одному, с замером прироста; неудачный удаляется | SPEC | §9 | 3 | PLANNED |
| X-02 | Export Sales в фазе 3 | EXEC/ADR-04 | §5.3 | 3 | PENDING_ADR |
| X-03 | Маркеры: календарь, погода, режим, рыночная аномалия как kill-switch | SPEC | §8 | 3–4 | PLANNED; базис — PENDING_ADR (OI-08) |
| X-04 | Маркер концентрации OI на бесплатных данных CME | SPEC | §6.3, §14 | 3 | BLOCKED_DATA (история) |
| X-05 | B4 change-point, PIT-детектор | SPEC | §3, §9 | 4A | PLANNED |
| X-06 | NG отдельной ветвью, газовый год, HDD/CDD, свои режимы | SPEC | §5.5 | 4B | PLANNED |
| X-07 | Односторонний экспорт записи, не раньше фазы 4 | SPEC | §11 | 4C | PLANNED |
| X-08 | Breeden–Litzenberger, раздельно с реальной плотностью | SPEC/ADR-04 | §3, §6.3 | 5 | DEFERRED |
| X-09 | Изоляция от quantum-core: отдельный репозиторий, без общего кода | SPEC | §11 | все | DONE (репозиторий не содержит ссылок/кода quantum-core) |
| X-10 | Без исполнения, ордеров, брокеров | SPEC | §1 | все | DONE (нет такого кода) |

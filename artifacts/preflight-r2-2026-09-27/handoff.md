# CERES — передача результата на аудит: PREFLIGHT, ревизия 2

Заполнено по шаблону `docs/source/CERES_AUDIT_HANDOFF_TEMPLATE_v1.0.md` (v1.0).
Пустое поле не означает PASS; неприменимое — NOT_APPLICABLE с объяснением; незапущенное — NOT_RUN.

## 1. Идентификация

- Фаза/подфаза: предпроектный аудит (PREFLIGHT), ревизия 2 — ответ на рецензию `docs/reviews/CERES_PREFLIGHT_REVIEW_v1.0.md` (вердикт рецензии: CHANGES_REQUIRED)
- Репозиторий или архив исходного кода: `https://github.com/Anderson-Hans/ceres`, ветка `claude/amazing-wozniak-p2kkig`
- Commit SHA / tag: содержимое пакета — commit, указанный в `artifacts/preflight-r2-2026-09-27/COMMIT` (записывается отдельным последующим commit, чтобы SHA не зависел сам от себя); ревизия 1 — `9d4ebc2`
- Версия исходной спецификации и её SHA-256: v0.2, `db04298fdf4653eeecbb86eba581159f25bb4f0f50a71c8bfea38c9f75d44167` (проверено: совпадает)
- Версия проект-промпта: v1.0, SHA-256 `9c9236a6077c1eb952a2c46899395cdc13aaa92f2a5626af90a1aa0bd57f3060`
- Run ID: `preflight-r2-2026-09-27`
- Версия модели: NOT_APPLICABLE — моделей нет (стадия preflight); спецификация B2 — ADR-10 v1.0 (Proposed)
- Версия схемы: схема записи прогноза — NOT_APPLICABLE (определяется в фазе 0/1, ADR-03 → 1.0.0); схема конфигурации эксперимента — 0.2.0
- Версия и hash предрегистрации: 0.2.0-draft; SHA-256 файлов — `artifacts/preflight-r2-2026-09-27/reproducibility/content-hashes.txt` (`configs/experiment.yaml`, `configs/model-b2.yaml`, `configs/decision.yaml`, `docs/preregistration.md`)
- Дата фиксации предрегистрации: NOT_APPLICABLE — не заморожена (`status: DRAFT`)
- Дата первого доступа к текущему OOS: NOT_APPLICABLE — к реальному OOS доступа не было; рыночные и фундаментальные данные не открывались
- Ссылка/путь к неизменяемому аудит-пакету: `artifacts/preflight-r2-2026-09-27/` на commit из поля выше

## 2. Статус без смешения оснований

| Контур | Статус | Подтверждающий артефакт |
|---|---|---|
| Инженерный | PASS | `tests/results.xml` (34 passed, 0 skipped), `tests/coverage.txt` (90%), `experiment-verify.txt`, `reproducibility/repeat-run.md` |
| Данные | BLOCKED_DATA | `docs/data-readiness.md` v1.1 (ни одного источника на уровне E3), `docs/network-access-request.md`, `docs/eod-delivery-requirements.md` |
| Научный | NOT_APPLICABLE | Стадия preflight: научный гейт не предусмотрен и не запускался; синтетика (`synthetic/`) научным результатом не является; `STOP_SCIENCE` не установлен |
| Независимая приёмка | PENDING | — |

**Итог исполнителя:** READY_FOR_REVIEW.

**Следующая фаза:** запрещена до явной приёмки (`ACCEPT_PREFLIGHT`). Даже после неё научная часть фазы 0 ожидает данных (BLOCKED_DATA); переход к фазе 1 без данных не допускается.

## 3. Что реализовано

| Требование | Раздел v0.2 | Код | Тест | Статус |
|---|---|---|---|---|
| Исходная спецификация без изменений, проверка hash | — (промпт §15) | `src/ceres/preflight/spec.py` | `tests/unit/test_spec_integrity.py` | DONE |
| Машиночитаемая предрегистрация и её проверка; FROZEN только при Accepted ADR | §10 | `configs/experiment.yaml`, `src/ceres/preflight/experiment.py` | `tests/unit/test_experiment_config.py` | DONE (содержание — Proposed) |
| Стоп-критерий §10: отношение средних, двусторонний 95% ДИ | §10 | `configs/experiment.yaml: gate_phase2` | `test_spec_invariants_enforced` | DONE (конфигурация) |
| CRPS / Brier | §7.2 | `src/ceres/eval/crps.py` | `tests/unit/test_crps.py` | DONE |
| Блочные ДИ: PB, JK, JK2 | §10 | `src/ceres/eval/bootstrap.py` | `tests/unit/test_bootstrap.py` | DONE |
| Симуляционное исследование методов ДИ и правила фазы 1 | §12 в.1, §10 | `src/ceres/preflight/simstudy.py` | `tests/statistical/test_simstudy.py` | DONE (синтетика) |
| Спецификация B2 | §3, §9 | `configs/model-b2.yaml`, ADR-10 | `tests/unit/test_model_b2_config.py` | DONE (Proposed) |
| Команды фаз 0–5 не выполняются до приёмки | — | `src/ceres/cli.py` | `tests/unit/test_cli.py` | DONE |

**Дополнения проект-промпта / рецензии** (не дословное содержание v0.2): формализация §10 и
ДИ (ADR-05), правило фазы 1 с `B1_no_deciles` (ADR-01 п.4b), Export Sales в фазе 3 (ADR-04),
ESS ≥ 400 (ADR-03), спецификация B2 целиком (ADR-10), эпизодное взвешивание (ADR-11).
**Принятые ADR:** нет (все 11 — Proposed). **Отклонения от v0.2:** не вводились; интерпретации
(вес ZW = 0 в гейте; оболочка B1) вынесены на решение (OI-07, ADR-01).
**Не реализовано:** весь код фаз 0–5 (запрещено до приёмки).

**Изменённые файлы относительно ревизии 1 (`9d4ebc2`):**
- новые: `docs/decisions/ADR-10-b2-model-specification.md`, `docs/decisions/ADR-11-b1-episode-weighting.md`, `configs/model-b2.yaml`, `docs/eod-delivery-requirements.md`, `docs/network-access-request.md`, `docs/handoff/preflight-handoff.md`, `docs/reviews/CERES_PREFLIGHT_REVIEW_v1.0.md` (+ `SHA256SUMS`), `docs/source/CERES_AUDIT_HANDOFF_TEMPLATE_v1.0.md`, `src/ceres/preflight/simstudy.py`, `tests/statistical/test_simstudy.py`, `tests/unit/test_model_b2_config.py`, `artifacts/preflight-r2-2026-09-27/**`;
- изменённые: `docs/spec-audit.md`, `docs/data-readiness.md`, `docs/preregistration.md`, `docs/preregistration/CHANGELOG.md`, `docs/requirements-traceability.md`, `docs/runbook.md`, `docs/decisions/ADR-01…09`, `docs/source/SHA256SUMS`, `configs/experiment.yaml`, `src/ceres/cli.py`, `src/ceres/preflight/experiment.py`, `tests/unit/test_experiment_config.py`, `pyproject.toml`, `requirements.lock`, `README.md`, `.gitignore`;
- удалённые: `src/ceres/preflight/power.py`, `tests/statistical/test_power_simulation.py`, `artifacts/preflight-2026-09-27/**` (заменены исследованием; остаются в истории git).

## 4. Данные и PIT

- Источники, лицензии, инструменты/контрактные месяцы: NOT_RUN — данные не загружались. План: ZCZ, ZSX, ZWN (EOD, ≥ 20 лет, `docs/eod-delivery-requirements.md`); WASDE, Crop Progress, Grain Stocks (ESMIS); шкала лимитов CBOT (SER CME).
- Глубина EOD: неизвестна (не закуплено). Глубина доказанных vintages: **ноль** на уровне E3; есть отдельные архивные карточки (WASDE 1973-09-17, Crop Progress 1995-04-03, Grain Stocks 1995-06-30 — E2, проверены рецензентом) и URL в поисковом индексе (E1).
- Пригодная выборка по годам: не может быть указана.
- event_time / vintage_time / revised / retrieved, единицы, ключ версии, raw hash, парсер, freshness: определены проектно (ADR-03, ADR-08); на данных не применялись — NOT_RUN.
- Неархивированные/неизвестные vintages: неизвестно (E0–E2).
- Отсутствующие контрактные месяцы и периоды: неизвестно.
- Ценовые лимиты: переменные лимиты CBOT с 2014-05-01 — только по поисковому индексу (E1); до 2014 — не установлено; текущая таблица задним числом не применяется; неизвестное → `unknown`.
- Basis/спреды/OI для маркеров: источников нет; индикатор базиса сохранён, оценка готовности — до фазы 3.
- Расхождение закупленной и пригодной истории: NOT_APPLICABLE (ничего не закуплено).
- Ограничения передачи данных аудитору: неизвестны до выбора вендора.
- Dataset manifest; PIT-кейсы (будущая ревизия не видна; публикация позже as_of в тот же день не видна); проверка отсутствия будущих целевых цен: NOT_APPLICABLE на preflight (`tests/pit-leakage-report.md`) — блокирующие тесты фазы 0.

## 5. Что реально запускалось

| Проверка/команда | Среда | Входы | Результат | Лог |
|---|---|---|---|---|
| `python -m ceres.cli spec verify` | venv по `requirements.lock`, CPython 3.11.15, Linux x86_64 | `docs/source/CERES-spec-v0.2.md` | OK | `experiment-verify.txt` |
| `python -m ceres.cli experiment verify` | то же | `configs/experiment.yaml`, ADR | engineering PASS; 9 ADR не приняты; 10 открытых OI | `experiment-verify.txt` |
| `pytest -q --cov=ceres` (unit + статистические) | то же | fixtures в коде тестов | 34 passed, 0 failed, 0 skipped; покрытие 90% | `tests/results.xml`, `tests/coverage.txt` |
| `preflight simstudy` — прогон B (официальный) | то же, 1 CPU | seed 20260927, синтетика | 100 ячеек, 120 000 повторений | `synthetic/simstudy/simstudy-run.log` |
| `preflight simstudy` — прогон C (повтор) | то же, параллельный процесс | то же | побитово совпал с B по всем 5 детерминированным файлам | `reproducibility/repeat-run.md`, `reproducibility/simstudy-run-C.log` |
| Сверка прогонов A и B | то же | CSV повторений | 0 различий в 25 общих столбцах × 120 000 строк | `reproducibility/repeat-run.md` |
| Проверка хостов источников | среда исполнителя | curl / WebFetch | отклонено egress-политикой | `docs/data-readiness.md` §2 |
| Integration, live smoke, реальный walk-forward, внешняя публикация | — | — | NOT_RUN (нет кода фаз 0+ и данных) | — |

Skipped: нет.

## 6. Научный результат

NOT_APPLICABLE для предпроектного аудита: модели не обучались, реальный OOS не существует,
научный гейт не предусмотрен. Поля таблиц и раздела «Для фазы 2» не заполняются.

Для сведения (не научный результат, синтетика, `synthetic/simstudy/`): процедура §10
проверена на заданном DGP; основной кандидат ДИ — JK2 (единственный, прошедший
зарегистрированный критерий (A)); частота прохождения §10 внутри DGP при 10–15 OOS-годах
и истинном skill 1–3% — 8–34%; правило фазы 1 при весе 1/H проходится в 4–34%
повторений. Эти числа не прогнозируют результат CERES.

## 7. Диагностика, отказы и маркеры

- r_hat, n_eff, PPC: NOT_APPLICABLE (MCMC не запускался; правила — ADR-03, ADR-10 п.9).
- ABSTAIN по причинам, доступность обязательных источников, невычисленные маркеры: NOT_APPLICABLE (прогнозов нет); схема причин и приоритетов — ADR-03 п.8, `configs/decision.yaml`.
- `NOT_EVALUATED` ≠ отсутствие аномалии — закреплено в ADR-03 и ADR-04 v1.1.
- Фазы 3/4/5: NOT_APPLICABLE.

## 8. Воспроизводимость

- Установка/запуск: `artifacts/preflight-r2-2026-09-27/reproducibility/commands.sh`; `docs/runbook.md`.
- Lock-file: `requirements.lock` (uv pip compile; numpy 2.4.6, scipy 1.17.1, pyyaml 6.0.3, pytest 9.1.1, pytest-cov 7.1.0).
- Runtime/устройство/backend/потоки: CPython 3.11.15, Linux x86_64, CPU; NumPy/SciPy без явной многопоточности (`reproducibility/environment.txt`); JAX/NumPyro не используются на этой стадии.
- Seeds: мастер 20260927; seed ячейки = `SeedSequence(20260927, spawn_key=(индекс ячейки в полной сетке,))`; эталоны — `SeedSequence([20260927, 7, индекс эталона])`.
- Resolved config и hashes: `config-resolved.yaml`, `preregistration-snapshot/`, `reproducibility/content-hashes.txt`.
- Повторный запуск: два полных прогона исследования побитово совпали (CSV повторений, сводки JSON/MD, допустимость, метаданные). Операционные метки времени есть только в `*.log`.
- Побитовое совпадение на другом CPU/BLAS не обещается.
- Недоступные аудитору проверки: нет — всё на этой стадии воспроизводимо offline без ключей, лицензий и raw-данных.

## 9. Нерешённые проблемы

| ID | Важность | Тип | Описание | Воспроизведение | Следствие |
|---|---|---|---|---|---|
| P-01 | BLOCKER | data | Нет ни одного источника на уровне E3 (WASDE, Crop Progress, Grain Stocks, шкала лимитов); сеть к хостам закрыта | `docs/data-readiness.md` §2 | Научная часть фазы 0 — BLOCKED_DATA |
| P-02 | BLOCKER | data | EOD не закуплен | — | То же |
| P-03 | BLOCKER | spec | ADR-01…ADR-11 не приняты; предрегистрация не заморожена | `python -m ceres.cli experiment verify` | Фаза 0 не разрешена |
| P-04 | MAJOR | science | Внутри DGP B1 (10 децилей, вес 1/H, 10 training-лет) в среднем хуже B0; P(фаза 1) 0.04–0.34 | `simstudy-summary.md`, раздел «Правило фазы 1» | Риск провала фазы 1 при наличии сигнала; решение по ADR-11 до OOS |
| P-05 | MAJOR | science | Низкая чувствительность §10 при ≤ 15 OOS-годах внутри DGP | ADR-05 п.2.8 | Интерпретация остановки; максимизация числа честных лет |
| P-06 | MINOR | science | Верхняя граница двустороннего ДИ занижена при skill > 0 у всех методов (критерий (B) не пройден) | `simstudy-admissibility.json` | Верхний конец ДИ не интерпретируется как 97.5%-граница; гейт — по нижней |
| P-07 | MINOR | science | JK не прошёл (A) пограничным образом (0.0345 и 0.0325 при пороге 0.032) | там же | Основной — JK2; JK — чувствительность |
| P-08 | MINOR | code | Покрытие `cli.py` 72% (ветви команд, возвращающих NOT_RUN, и печать) | `tests/coverage.txt` | Нет влияния на методику |

Связанные тесты: P-03 — `test_freezing_requires_accepted_adrs`; P-06/P-07 — `test_admissibility_flags_excess_lower_tail_error`; P-04 — `test_phase1_rule_requires_both_comparisons`.
При изменении ADR-05/ADR-01/ADR-11 или DGP исследование пересчитывается целиком (`commands.sh`); реальных метрик и гейтов для пересчёта нет.

## 10. Заключение исполнителя

**Что подтверждено:** неизменность спецификации; структурная согласованность предрегистрации с v0.2 и рецензией (проверка кодом); корректность CRPS/Brier и процедур ДИ на контролируемых примерах; поведение методов ДИ на зарегистрированном синтетическом DGP с оценкой MCSE; побитовая воспроизводимость исследования.

**Что не подтверждено:** доступность и полнота PIT-истории любого источника; наличие исторической шкалы лимитов; глубина и права на EOD; поведение CERES на реальных данных; допустимость методов ДИ вне зарегистрированного DGP.

**Отрицательные результаты:** iid-интервал по строкам и перцентильная переоценка годовых блоков недопустимы по критерию (A); JK — пограничный провал (A); ни один метод не проходит (B); B1 с весом 1/H в DGP переобучается; чувствительность §10 при 10–15 OOS-годах внутри DGP низкая.

**Ограничения:** синтетический DGP упрощён (гауссовские прогнозы, известная волатильность, фиксированное окно обучения, одно значение признака на год); эталоны skill — с MCSE; ни одно число исследования не переносится на рынок.

**Основание перехода/остановки:** переход к фазе 0 — только после `ACCEPT_PREFLIGHT`; научная часть фазы 0 останется BLOCKED_DATA до снятия P-01/P-02. Оснований для `STOP_SCIENCE` нет — научный гейт не запускался.

**Какие решения требуются от аудитора:** OI-01 (ADR-01…11), OI-02 (B2 = ADR-10), OI-05 (JK2), OI-06 (правило фазы 1), OI-07 (вес ZW), OI-10 (ADR-11: вес 1 на эпизод), открытый вопрос ADR-01 (B0 vs сильнейший вариант), доступ к хостам источников, решение о закупке EOD (владелец, отдельно).

---

# Раздел независимого аудитора — исполнитель не заполняет

Проверенный commit и run ID:
Проверенные материалы:
Воспроизведённые команды:
Невоспроизведённые утверждения:
Блокирующие замечания:
Научный гейт:
Решение: ACCEPT_PREFLIGHT / ACCEPT_PHASE_N / CHANGES_REQUIRED /
BLOCKED_DATA / STOP_SCIENCE.
Условия следующей фазы:

# Отчёт рубежа PREFLIGHT, ревизия 2 — пакет на приёмку

**run_id:** `preflight-r2-2026-09-27` · **Дата:** 2026-09-27 · **Состояние:** `READY_FOR_REVIEW`

```
engineering: PASS
data:        BLOCKED_DATA
science:     NOT_APPLICABLE
review:      PENDING
```

Полный отчёт по шаблону аудитора — [`handoff.md`](handoff.md) (копия `docs/handoff/preflight-handoff.md`).
Аудит спецификации — `docs/spec-audit.md` v1.1 (§9 — изменения по пунктам рецензии, §6 — OI → решение → блокер → фаза).

## Состав пакета

| Путь | Содержание |
|---|---|
| `status.json` | статусы без смешения оснований |
| `run-manifest.json` | версии, seeds, команда исследования |
| `handoff.md` | заполненный шаблон передачи на аудит |
| `config-resolved.yaml`, `preregistration-snapshot/` | предрегистрация 0.2.0-draft (DRAFT) |
| `requirements-traceability.md` | трассировка v1.1 |
| `experiment-verify.txt` | вывод `spec verify` и `experiment verify` |
| `tests/` | `results.xml` (34 passed), `coverage.txt` (90%), `summary.md`, `pit-leakage-report.md` (NOT_APPLICABLE) |
| `synthetic/simstudy/` | **синтетика** (`is_synthetic: true`): все 120 000 повторений, метаданные DGP и эталонов, сводка, допустимость методов, лог |
| `science/`, `samples/` | NOT_APPLICABLE с объяснением |
| `reproducibility/` | окружение, команды, хэши, доказательство побитового повтора |

Фаза 0 не начата. Решение `ACCEPT_PREFLIGHT` / `CHANGES_REQUIRED` — за аудитором.

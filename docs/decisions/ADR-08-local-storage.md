# ADR-08. Локальное PIT-хранилище и provenance

**Статус:** Proposed
**Дата:** 2026-09-27
**Затрагивает:** §5.2, §5.4, §11 спецификации v0.2; §4.1–4.2 execution-промпта
**Тип:** [EXEC]

## Решение (предлагаемое)

- **Raw:** неизменяемые файлы в `data/raw/<observer>/<sha256>.<ext>`
  (content-addressed). Никогда не коммитятся в git (лицензии).
- **Факты:** Parquet, append-only; схема = поля `Evidence` §5.1
  (`observer, entity, feature, value, event_time, vintage_time, revision`)
  + ключ логического факта `(observer, entity, feature, event_time)`.
- **Provenance** (связанная таблица, ключ = id факта): источник, документ,
  URL, raw sha256, `retrieved_at`, версия парсера, единицы, идентификатор
  периода, регион, `vintage_confidence ∈ {exact, date_only, unknown}`.
- **Каталог/манифесты:** SQLite (`data/store/catalog.sqlite`): ingest-runs,
  manifests, quarantine.
- Идемпотентность: повторный ingest того же raw (тот же sha256) не
  создаёт фактов. Тот же ключ версии `(логический ключ, revision)` с
  другим значением → quarantine, не last-write-wins.
- Для экспорта в фазе 4 выбирается **файл** (атомарная запись через
  временный файл + rename), не очередь; очередь не реализуется заранее.

Альтернативы (DuckDB вместо SQLite, Delta/Iceberg) не нужны на объёмах
EOD и месячной статистики; могут быть пересмотрены отдельным ADR.

# ceres

**CERES** — вероятностный аналитический модуль сезонной товарки (ZC/ZS/ZW): калиброванные
предиктивные распределения лог-доходности контракта на 5 и 21 торговый день с правом
сказать «сигнала нет». Не торговый бот: исполнения, ордеров и брокеров нет.

**Текущая стадия: предпроектный аудит (`READY_FOR_REVIEW`).** Фаза 0 начинается только
после `ACCEPT_PREFLIGHT`.

| Документ | Назначение |
|---|---|
| [docs/source/](docs/source/) | Исходная спецификация v0.2 и execution-промпт v1.0 (без изменений, SHA-256) |
| [docs/spec-audit.md](docs/spec-audit.md) | Аудит: противоречия, ответы на §12, риски, блокеры, план фаз |
| [docs/decisions/](docs/decisions/) | ADR-01…ADR-09 (Proposed) |
| [docs/requirements-traceability.md](docs/requirements-traceability.md) | Требование → раздел → код → тест → артефакт → фаза |
| [docs/data-readiness.md](docs/data-readiness.md) | Готовность данных (`BLOCKED_DATA`) |
| [docs/preregistration.md](docs/preregistration.md) | Черновик предрегистрации (`configs/experiment.yaml`) |
| [artifacts/preflight-2026-09-27/](artifacts/preflight-2026-09-27/) | Пакет на приёмку |

```bash
uv venv --python 3.11 .venv && . .venv/bin/activate
uv pip install -r requirements.lock && uv pip install -e . --no-deps
python -m ceres.cli spec verify
python -m ceres.cli experiment verify
python -m pytest -q
```

Изоляция: отдельный репозиторий, без общего кода и интеграции с quantum-core (§11 спецификации).

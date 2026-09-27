# Повторный запуск симуляционного исследования

Два независимых полных прогона одной командой в одном окружении (одновременно, разные процессы):
- прогон B → `artifacts/preflight-r2-2026-09-27/synthetic/simstudy/` (официальный)
- прогон C → временный каталог (лог — `reproducibility/simstudy-run-C.log`)

| Файл | SHA-256 прогона B | SHA-256 прогона C | Совпадение |
|---|---|---|---|
| simstudy-replicates.csv.gz | `b35ae465a8fc5c21834b0d4a6dea87f6939537ef17890686875b28b68650be8c` | `b35ae465a8fc5c21834b0d4a6dea87f6939537ef17890686875b28b68650be8c` | побитово |
| simstudy-summary.json | `d7a99c977e4d6cd7f7eecbc1a65929cf89d11b8ee70c911d521ab966b5afa5d2` | `d7a99c977e4d6cd7f7eecbc1a65929cf89d11b8ee70c911d521ab966b5afa5d2` | побитово |
| simstudy-summary.md | `3285356b32dd83b860d5343d0e6927a8e5b12442ad2d56eabef9581dd1f2cc48` | `3285356b32dd83b860d5343d0e6927a8e5b12442ad2d56eabef9581dd1f2cc48` | побитово |
| simstudy-admissibility.json | `35ba53a71488eddfe1a363c4c1e260071de179eec37ff5aeafa2d82be04db9c8` | `35ba53a71488eddfe1a363c4c1e260071de179eec37ff5aeafa2d82be04db9c8` | побитово |
| simstudy-metadata.json | `68c79e5a2a0362f2cb7f8e219882d4ad95db0eca6674895e8690509294e25517` | `68c79e5a2a0362f2cb7f8e219882d4ad95db0eca6674895e8690509294e25517` | побитово |

Операционные метки времени есть только в `simstudy-run.log` (не входят в детерминированное содержание).

Дополнительно: прогон A (код до добавления столбцов эпизодного взвешивания B1, тот же seed) и прогон B совпали во всех 25 общих столбцах всех 120 000 повторений (0 различающихся ячеек); новые столбцы B: brier_B1ep, brier_B1ndep, phase1_pass_ep (они не расходуют случайные числа). Файлы прогона A в пакет не включены.

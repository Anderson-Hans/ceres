# Запрос сетевого доступа (под текущую стадию)

**Версия:** 1.0 · **Дата:** 2026-09-27
**Текущая стадия:** PREFLIGHT (разрешены проверка источников и воспроизводимая симуляция;
фаза 0 не начата). Доступ запрашивается **только** для проверки источников фазы 0–1:
загрузка образцов, фиксация raw hash, разбор полей (переход E1/E2 → E3 в
`docs/data-readiness.md`).

Как меняется: владелец окружения → настройки облачного окружения (меню окружения в
заголовке сессии → Edit) → Network access → добавить хосты в список разрешённых.

## Хосты и переходы загрузки

| Хост | Пути | Назначение | Стадия |
|---|---|---|---|
| `esmis.nal.usda.gov` | `/publication/world-agricultural-supply-and-demand-estimates*`, `/publication/crop-progress*`, `/publication/grain-stocks*` (карточки и списки выпусков); `/sites/default/release-files/**` (файлы выпусков: PDF/TXT/XLS/XML) | архивы WASDE, Crop Progress, Grain Stocks | preflight (проверка), фаза 0 |
| `www.cmegroup.com` | `/trading/price-limits.html` (текущая таблица — только для сверки); `/content/dam/cmegroup/tools-information/lookups/advisories/ser/**`, `/tools-information/lookups/advisories/ser/**` (Special Executive Reports — история изменений лимитов); страницы спецификаций ZC/ZS/ZW и календаря торгов | история лимитов, FND/LTD, календарь | preflight (проверка), фаза 0 |
| `quickstats.nass.usda.gov` | `/api/**` | только сверка текущих значений с архивными выпусками (не PIT-источник) | фаза 0 |

Если при загрузке выяснится, что файлы выпусков отдаются с другого хоста (редирект),
этот хост будет добавлен в запрос отдельной строкой с указанием перехода.

## Не запрашивается сейчас

- `apps.fas.usda.gov`, `www.ncei.noaa.gov`, `www.cftc.gov` — фаза 3.
- `api.eia.gov` — фаза 4.
- Хост вендора EOD — после решения о закупке.
- `usda.library.cornell.edu` — прежний адрес архива ESMIS; не требуется, если
  `esmis.nal.usda.gov` отдаёт те же выпуски (проверить при доступе).

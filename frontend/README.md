# Фронтенд CRM

React 19 + TypeScript + Vite, интерфейс — Ant Design 6, данные — TanStack Query, графики — recharts.
Запуск и общее описание проекта — в [README в корне](../README.md).

```bash
npm ci
npm run dev        # http://localhost:5173, /api проксируется на 127.0.0.1:8000
npx tsc -b         # проверка типов
npm run lint       # oxlint
npm run build      # сборка в dist/
```

## Устройство

| Путь | Что там |
|---|---|
| `src/api/client.ts` | axios: JWT в заголовке, автообновление access-токена, массивы в query как `a=1&a=2` |
| `src/api/hooks.ts` | `useList`, `useDetail`, `useApiAction` (мутация + уведомление + обновление данных), разбор ошибок DRF |
| `src/api/types.ts`, `statuses.ts` | типы ответов API, статусы и их цвета |
| `src/auth/AuthContext.tsx` | текущий пользователь, `can(...roles)`, `canManageDepartment` |
| `src/components/nav.ts` | меню и права разделов — единый источник для меню и маршрутов |
| `src/components/CrudPage.tsx` | таблица справочника с поиском и модальной формой |
| `src/components/DocumentList.tsx`, `LinesFormList.tsx` | список документов и редактор строк документа |
| `src/components/charts/` | графики и плитки KPI по правилам визуализации (проверенная палитра, табличный вид) |
| `src/pages/` | страницы; грузятся лениво (см. `App.tsx`) |

Десятичные числа приходят из API строками (без потери точности) и форматируются в `src/utils/format.ts`.

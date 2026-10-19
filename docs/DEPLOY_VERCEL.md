# Деплой на Vercel

Как развернуть CRM на [vercel.com](https://vercel.com): бэкенд на Django, фронтенд на React и база PostgreSQL.
Время — около 30 минут при первом разе.

> Учебный проект. На публичном адресе любой может открыть страницу входа — не оставляйте демо-пароль
> `demo12345` (см. шаг 3).

## Схема

```
браузер ──► crm-frontend.vercel.app ──┬─ /, /orders, … ─► статика React (dist/)
                                      └─ /api/*  ─────► crm-backend.vercel.app/api/*  (Django, функция Vercel)
                                                                │
                                                                └─► Neon Postgres
```

- **Два проекта Vercel из одного репозитория:** бэкенд (корень репозитория) и фронтенд (папка `frontend`).
- **Фронтенд проксирует `/api`** на бэкенд (`frontend/vercel.json`), поэтому браузер видит один домен, и CORS не нужен.
- **База — PostgreSQL (Neon из Vercel Marketplace).** SQLite на Vercel не подойдёт: файловая система функций
  временная, данные пропадут.
- **Админка и Swagger** открываются на домене бэкенда: `https://<бэкенд>/admin/`, `/swagger/`.

Почему не один проект: в одном проекте Vercel тоже можно держать Python и фронтенд (Vercel Services), но эта
возможность пока в бета-версии. Два обычных проекта — стабильный путь.

## Что уже подготовлено в репозитории

| Файл | Зачем |
|---|---|
| `vercel.json` | Настройки функции бэкенда: время ответа до 60 с, из сборки исключены `frontend/`, `tests/`, `docs/` |
| `frontend/vercel.json` | Прокси `/api` → бэкенд и отдача `index.html` для всех адресов SPA |
| `.python-version` | Python 3.12 |
| `requirements.txt` | Единственный источник зависимостей. `pyproject.toml` в проекте нет намеренно: если он есть, Vercel берёт зависимости из него |
| `core/settings.py` | Всё из переменных окружения; `SECURE_PROXY_SSL_HEADER` и `CSRF_TRUSTED_ORIGINS` для работы за прокси Vercel; secure-cookies при `DEBUG=False` |

Vercel распознаёт Django сам: находит `manage.py`, берёт точку входа из `WSGI_APPLICATION` (`core.wsgi.application`),
устанавливает зависимости и при сборке выполняет `collectstatic` (потому что задан `STATIC_ROOT`), а статику раздаёт
со своего CDN.

## 0. Перед началом

- Аккаунт на vercel.com, вход через GitHub.
- Репозиторий запушен на GitHub вместе с файлами из таблицы выше.
- Локально работает `python manage.py runserver` — понадобится, чтобы применить миграции к облачной базе.

## 1. Проект бэкенда

1. Vercel → **Add New… → Project** → выберите репозиторий → **Import**.
2. Настройки проекта:
   - **Project Name:** например, `crm-backend-<ваш ник>` (имя станет доменом `…vercel.app`, оно должно быть уникальным).
   - **Framework Preset:** Django (определится сам).
   - **Root Directory:** оставьте `./` (корень репозитория).
3. **Environment Variables** — добавьте:

   | Переменная | Значение |
   |---|---|
   | `SECRET_KEY` | случайная строка, см. команду ниже |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.vercel.app` (позже можно сузить до точного домена бэкенда) |
   | `CSRF_TRUSTED_ORIGINS` | `https://<домен-бэкенда>.vercel.app` — нужен для входа в админку |

   Сгенерировать `SECRET_KEY`:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
4. **Deploy.** Первая сборка пройдёт и без базы: `collectstatic` к базе не обращается.

## 2. База данных

1. В проекте бэкенда: **Storage → Create Database → Neon (Postgres)** → создайте базу и подключите её к проекту
   (окружения Production и Preview).
2. Интеграция сама добавит в переменные окружения проекта строку подключения `DATABASE_URL` (и рядом —
   вариант без пулера, обычно `DATABASE_URL_UNPOOLED`). Проверьте в **Settings → Environment Variables**:
   переменная должна называться именно `DATABASE_URL` — её читает `core/settings.py`.
3. **Redeploy** проекта бэкенда (Deployments → … → Redeploy), чтобы функция получила `DATABASE_URL`.

## 3. Миграции и данные

Vercel не запускает `migrate` сам — схему базы создают с вашего компьютера, подключившись к облачной базе.

1. Скопируйте строку подключения **без пулера** (`DATABASE_URL_UNPOOLED` в переменных проекта или Connection string
   на странице базы в Storage; должна содержать `sslmode=require`).
2. В корне проекта, с активированным `.venv`:
   ```bash
   export DATABASE_URL='postgresql://…?sslmode=require'
   python manage.py migrate
   ```
3. Данные — один из вариантов:
   - **Демо-набор** со своим паролем для всех демо-пользователей (не используйте общеизвестный `demo12345`):
     ```bash
     python manage.py seed_demo --password 'придумайте-надёжный-пароль'
     ```
     По сети это занимает несколько минут.
   - **Пустая система** с одним администратором:
     ```bash
     python manage.py createsuperuser
     ```
4. Закройте терминал или выполните `unset DATABASE_URL`, чтобы локальный `runserver` снова работал с SQLite.

## 4. Проверка бэкенда

- `https://<бэкенд>/api/auth/users/me/` → `{"detail": "Учетные данные не были предоставлены."}` (401) — Django и база отвечают.
- `https://<бэкенд>/admin/` → оформленная страница входа (если без стилей — см. «Ошибки»).
- `https://<бэкенд>/swagger/` → документация API.

## 5. Проект фронтенда

1. В `frontend/vercel.json` замените `ЗАМЕНИТЕ-НА-ДОМЕН-БЭКЕНДА.vercel.app` на домен бэкенда из шага 1,
   закоммитьте и запушьте:
   ```json
   { "source": "/api/(.*)", "destination": "https://crm-backend-ваш-ник.vercel.app/api/$1" }
   ```
   Именно регулярное выражение `(.*)`, а не `/api/:path*`: шаблон `:path*` не совпадает с путями, которые
   заканчиваются на `/`, а в Django-API так заканчиваются все адреса.
2. Vercel → **Add New… → Project** → тот же репозиторий → **Import**.
3. Настройки:
   - **Project Name:** например, `crm-<ваш ник>`.
   - **Root Directory:** `frontend` (кнопка Edit).
   - **Framework Preset:** Vite (определится сам; сборка `npm run build`, папка `dist`).
   - Переменные окружения не нужны.
4. **Deploy.**

## 6. Проверка целиком

Откройте домен фронтенда → войдите пользователем из шага 3 → проверьте, что открываются заказы, остатки и дашборд.
Ссылки вида `/orders/5` должны открываться и при обновлении страницы (это делает второе правило в `frontend/vercel.json`).

## Обновления

- Push в `master` пересобирает оба проекта автоматически.
- Если изменились модели — после деплоя примените миграции к облачной базе (шаг 3, только `migrate`).
  Безопаснее делать изменения схемы обратно совместимыми: старый код какое-то время работает с новой схемой.
- Preview-деплои (из веток и pull request) фронтенда ходят в **production-бэкенд и боевую базу** — учитывайте это,
  если тестируете на них изменения данных.

## Ограничения бесплатного хостинга функций

- Бэкенд — бессерверная функция: после простоя первый запрос медленнее («холодный старт»).
- Нет постоянного диска: загружаемых файлов в проекте нет, но SQLite и `MEDIA_ROOT` на Vercel не работают.
- Нет фоновых процессов: всё в проекте выполняется в рамках запроса, так что это не мешает.
- Логи: проект → **Logs** (ошибки Django видны там, `DEBUG` в продакшене выключен).

## Ошибки и что делать

| Симптом | Причина и решение |
|---|---|
| Сборка бэкенда падает с `ImproperlyConfigured: Set the SECRET_KEY` | Не задан `SECRET_KEY` (переменные окружения применяются и к сборке) |
| `ModuleNotFoundError: No module named 'django'` | В корне появился `pyproject.toml` без зависимостей — Vercel взял его вместо `requirements.txt`. Удалите его или перенесите зависимости в `[project]` |
| `400 Bad Request` | Домен не входит в `ALLOWED_HOSTS` |
| `403 CSRF verification failed` при входе в админку | В `CSRF_TRUSTED_ORIGINS` нет `https://<домен-бэкенда>` |
| Админка без стилей | Не задан `STATIC_ROOT` или статика не собралась — смотрите лог сборки, шаг `collectstatic` |
| `relation "…" does not exist` в логах | Не применены миграции (шаг 3) |
| `could not connect to server` / таймаут базы | Нет `DATABASE_URL` в Production или забыли Redeploy после подключения базы |
| Во фронтенде «Сервер недоступен» или 404 на `/api/…` | В `frontend/vercel.json` не тот домен бэкенда |
| «API не отвечает (HTTP 405)», `/api/…/` отдаёт HTML приложения | Правило прокси не срабатывает на пути со слешем в конце — используйте `"/api/(.*)"` → `…/api/$1` |
| Вместо данных — страница входа Vercel (401) | На бэкенде включена Deployment Protection для этого домена; production-домен должен быть публичным (Settings → Deployment Protection) |

## Полезные ссылки

- [Deploy a Django app on Vercel](https://vercel.com/docs/frameworks/full-stack/django)
- [Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Rewrites](https://vercel.com/docs/rewrites)
- [Services (бета)](https://vercel.com/docs/services)

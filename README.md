# Django DRF Starter

[![CI](https://github.com/marse11e/django-project-template-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/marse11e/django-project-template-v2/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Шаблон для быстрого старта Django + DRF проекта. Из коробки — JWT-аутентификация, Swagger-документация, красивая админка и полная настройка через `.env`. Никаких захардкоженных секретов и настроек в коде.

---

## Содержание

- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Переменные окружения](#переменные-окружения)
- [База данных](#база-данных)
- [Docker](#docker)
- [Аутентификация](#аутентификация)
- [API-документация](#api-документация)
- [Создание нового приложения](#создание-нового-приложения)
- [Структура проекта](#структура-проекта)
- [Тесты и CI](#тесты-и-ci)
- [Деплой](#деплой)
- [Лицензия](#лицензия)

---

## Стек

| Пакет | Назначение |
|---|---|
| [Django](https://www.djangoproject.com/) | Основной фреймворк |
| [Django REST Framework](https://www.django-rest-framework.org/) | REST API |
| [djoser](https://djoser.readthedocs.io/) | Готовые эндпоинты аутентификации |
| [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/) | JWT-токены |
| [drf-yasg](https://drf-yasg.readthedocs.io/) | Swagger / ReDoc документация |
| [django-environ](https://django-environ.readthedocs.io/) | Чтение настроек из `.env` |
| [django-jazzmin](https://django-jazzmin.readthedocs.io/) | Тема для Django Admin |
| [Pillow](https://pillow.readthedocs.io/) | Работа с изображениями |
| [psycopg2-binary](https://www.psycopg.org/) | Драйвер PostgreSQL |

---

## Быстрый старт

### Локально (без Docker)

```bash
# 1. Создать папку проекта и клонировать шаблон
mkdir my-project
cd my-project
git clone https://github.com/marse11e/django-project-template-v2 .

# 2. Создать и активировать виртуальное окружение
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить переменные окружения
cp .env.example .env
# Открой .env и при необходимости измени значения

# 5. Применить миграции
python manage.py migrate

# 6. Запустить сервер
python manage.py runserver
```

Проект доступен на [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Через Docker

```bash
mkdir my-project
cd my-project
git clone https://github.com/marse11e/django-project-template-v2 .
cp .env.example .env
docker compose up --build
```

Проект доступен на [http://localhost:8000](http://localhost:8000). PostgreSQL и миграции поднимаются автоматически.

---

## Переменные окружения

Все настройки проекта задаются через файл `.env`. Шаблон со всеми переменными находится в `.env.example`.

```bash
cp .env.example .env
```

### Полный список переменных

| Переменная | По умолчанию | Обязательно менять перед продом | Описание |
|---|---|---|---|
| `SECRET_KEY` | *(задан в .env.example)* | **Да** | Секретный ключ Django. Генерируй новый для каждого проекта. |
| `DEBUG` | `True` | **Да** | Режим отладки. В продакшне всегда `False`. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | **Да** | Разрешённые хосты через запятую. В продакшне — реальный домен. |
| `DATABASE_URL` | *(не задан → SQLite)* | Нет | URL подключения к БД. Не задан — используется SQLite. |
| `STATIC_ROOT` | `staticfiles` | Нет | Папка для `collectstatic`. |
| `MEDIA_ROOT` | `media` | Нет | Папка для загружаемых файлов. |
| `LANGUAGE_CODE` | `ru` | Нет | Язык интерфейса Django. |
| `TIME_ZONE` | `Asia/Almaty` | Нет | Часовой пояс. |
| `POSTGRES_DB` | `django_db` | Нет | Имя БД (только для Docker). |
| `POSTGRES_USER` | `django_user` | Нет | Пользователь БД (только для Docker). |
| `POSTGRES_PASSWORD` | `django_pass` | Нет | Пароль БД (только для Docker). |

### Генерация нового SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Вставь результат в `.env`:

```dotenv
SECRET_KEY=полученная-строка
```

---

## База данных

### SQLite (по умолчанию)

Никакой настройки не нужно. После `python manage.py migrate` в корне проекта создастся файл `db.sqlite3`. Подходит для локальной разработки.

### PostgreSQL

Достаточно одной строки в `.env`:

```dotenv
DATABASE_URL=postgres://user:password@localhost:5432/dbname
```

После этого запусти миграции:

```bash
python manage.py migrate
```

Никаких правок кода не требуется — переключение полностью через переменную окружения.

---

## Docker

Проект поставляется с готовым `Dockerfile` и `docker-compose.yml`.

### Запуск (Django + PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

Что происходит при запуске:
1. Собирается образ Django-приложения на базе `python:3.12-slim`.
2. Поднимается контейнер PostgreSQL 17 с проверкой готовности (healthcheck).
3. После того как БД готова — автоматически накатываются миграции.
4. Запускается `runserver` на порту `8000`.

### Полезные команды

```bash
# Запуск в фоне
docker compose up -d --build

# Остановка
docker compose down

# Остановка с удалением данных БД
docker compose down -v

# Логи
docker compose logs -f web

# Выполнить команду внутри контейнера
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell
```

### Только сборка образа

```bash
docker build -t django-drf-starter .
```

---

## Аутентификация

Аутентификация реализована через `djoser` + `djangorestframework-simplejwt`. Все запросы к защищённым эндпоинтам требуют заголовок `Authorization: Bearer <access_token>`.

### Создать суперпользователя

```bash
python manage.py createsuperuser
```

### Получить токен

```bash
curl -X POST http://127.0.0.1:8000/api/auth/jwt/create/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_password"}'
```

Ответ:

```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

- **access** — короткоживущий токен для запросов к API.
- **refresh** — долгоживущий токен для получения нового access-токена.

### Обновить access-токен

```bash
curl -X POST http://127.0.0.1:8000/api/auth/jwt/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

### Проверить токен

```bash
curl -X POST http://127.0.0.1:8000/api/auth/jwt/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "<access_token>"}'
```

### Использовать токен в запросах

```bash
curl http://127.0.0.1:8000/api/some-endpoint/ \
  -H "Authorization: Bearer <access_token>"
```

### Все эндпоинты аутентификации

| Метод | URL | Описание |
|---|---|---|
| `POST` | `/api/auth/users/` | Регистрация нового пользователя |
| `GET` | `/api/auth/users/me/` | Данные текущего пользователя |
| `POST` | `/api/auth/jwt/create/` | Получить access + refresh токены |
| `POST` | `/api/auth/jwt/refresh/` | Обновить access-токен |
| `POST` | `/api/auth/jwt/verify/` | Проверить токен |
| `POST` | `/api/auth/users/set_password/` | Изменить пароль |

---

## API-документация

Swagger и ReDoc доступны сразу после запуска сервера — без дополнительной настройки.

| Интерфейс | URL |
|---|---|
| Swagger UI | [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/) |
| ReDoc | [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/) |

Swagger поддерживает авторизацию по JWT: нажми кнопку **Authorize** и введи токен в формате `Bearer <access_token>`.

---

## Создание нового приложения

Для создания нового Django-приложения используй скрипт `create_app.py`. Он работает одинаково на Linux, macOS и Windows.

```bash
python create_app.py <name>
```

**Пример:**

```bash
python create_app.py blog
```

Скрипт автоматически:

1. Проверит, что имя — валидный Python-идентификатор в нижнем регистре (не зарезервированное слово).
2. Проверит, что папка `apps/blog/` ещё не существует — если существует, завершится без изменений.
3. Создаст приложение в `apps/blog/` через `manage.py startapp`.
4. Исправит `name` в `apps/blog/apps.py` с `"blog"` на `"apps.blog"`.
5. Создаст заглушки `apps/blog/urls.py` и `apps/blog/serializers.py` с примерами кода.
6. Добавит `"apps.blog"` в `INSTALLED_APPS` в `core/settings.py`.

После создания подключи маршруты приложения в `core/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    ...
    path("api/blog/", include("apps.blog.urls")),
]
```

### Структура созданного приложения

```
apps/blog/
├── migrations/
│   └── __init__.py
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py   # заглушка с примером ModelSerializer
├── tests.py
├── urls.py          # заглушка с примером роута
└── views.py
```

---

## Структура проекта

```
my-project/
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: lint → check → migrate → test
├── apps/                     # Пользовательские Django-приложения
│   └── __init__.py
├── core/                     # Конфигурация проекта
│   ├── __init__.py
│   ├── settings.py           # Все настройки через django-environ из .env
│   ├── urls.py               # Корневой роутер (admin, auth, swagger)
│   ├── asgi.py               # ASGI-точка входа
│   └── wsgi.py               # WSGI-точка входа
├── tests/
│   └── test_smoke.py         # Smoke-тесты: swagger, redoc, jwt, admin
├── .dockerignore             # Исключения для Docker-сборки
├── .env.example              # Шаблон переменных окружения
├── .gitignore
├── create_app.py             # Скрипт создания нового приложения
├── docker-compose.yml        # Django + PostgreSQL через Docker
├── Dockerfile                # Образ приложения на python:3.12-slim
├── manage.py
├── pyproject.toml            # Конфиг ruff и pytest
├── requirements.txt          # Prod-зависимости
├── requirements-dev.txt      # Dev-зависимости (ruff, pytest, pytest-django)
├── LICENSE
└── README.md
```

---

## Тесты и CI

### Установить dev-зависимости

```bash
pip install -r requirements-dev.txt
```

### Запустить тесты

```bash
pytest
```

### Запустить линтер

```bash
ruff check .
```

### Автоисправление ошибок линтера

```bash
ruff check --fix .
```

### Проверить конфигурацию Django

```bash
python manage.py check
```

### CI (GitHub Actions)

При каждом `push` и `pull_request` в ветку `main` автоматически выполняется:

1. Установка зависимостей из `requirements-dev.txt`.
2. `ruff check .` — проверка стиля кода.
3. `python manage.py check` — проверка конфигурации Django.
4. `python manage.py migrate` — применение миграций.
5. `pytest` — запуск тестов.

CI работает на SQLite без внешних сервисов — зелёный сразу после клонирования.

---

## Деплой

Перед деплоем на продакшн-сервер обязательно:

1. **Сгенерируй новый `SECRET_KEY`** и задай его в `.env`.
2. **Выставь `DEBUG=False`** — иначе Django отдаёт отладочные страницы с деталями ошибок.
3. **Укажи реальный домен в `ALLOWED_HOSTS`**, например: `ALLOWED_HOSTS=example.com,www.example.com`.
4. **Переключись на PostgreSQL** через `DATABASE_URL`.
5. **Собери статику:**

```bash
python manage.py collectstatic --noinput
```

6. **Настрой раздачу статики и медиа** через Nginx или облачное хранилище (S3 и т.п.) — `runserver` не подходит для продакшна.
7. **Используй Gunicorn или uWSGI** вместо `runserver`:

```bash
pip install gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

---

## Лицензия

[MIT](LICENSE)

#!/usr/bin/env python
"""
Скрипт для создания нового Django-приложения в папке apps/.

Использование:
    python create_app.py <name>

Пример:
    python create_app.py blog
"""

import keyword
import os
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / "apps"
SETTINGS_FILE = BASE_DIR / "core" / "settings.py"
MARKER = "# LOCAL_APPS_MARKER"


def validate_name(name: str) -> None:
    if not name.isidentifier():
        print(f"Ошибка: '{name}' — не валидный Python-идентификатор.")
        sys.exit(1)
    if keyword.iskeyword(name):
        print(f"Ошибка: '{name}' — зарезервированное слово Python.")
        sys.exit(1)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        print(f"Ошибка: '{name}' — имя должно состоять из строчных латинских букв, цифр и подчёркиваний.")
        sys.exit(1)


def check_not_exists(app_dir: Path) -> None:
    if app_dir.exists():
        print(f"Ошибка: папка '{app_dir}' уже существует. Приложение не создано.")
        sys.exit(1)


def run_startapp(name: str, app_dir: Path) -> None:
    app_dir.mkdir(parents=True, exist_ok=False)
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "manage.py"), "startapp", name, str(app_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        app_dir.rmdir()
        print(f"Ошибка при создании приложения:\n{result.stderr}")
        sys.exit(1)


def patch_apps_py(name: str, app_dir: Path) -> None:
    apps_py = app_dir / "apps.py"
    text = apps_py.read_text()
    text = text.replace(f'name = "{name}"', f'name = "apps.{name}"')
    text = text.replace(f"name = '{name}'", f"name = 'apps.{name}'")
    apps_py.write_text(text)


def create_urls_py(app_dir: Path) -> None:
    content = """\
from django.urls import path

# Пример:
# from . import views
#
# urlpatterns = [
#     path('', views.ExampleListView.as_view(), name='example-list'),
# ]

urlpatterns = []
"""
    (app_dir / "urls.py").write_text(content)


def create_serializers_py(app_dir: Path) -> None:
    content = """\
# Пример ModelSerializer:
#
# from rest_framework import serializers
# from .models import Example
#
# class ExampleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Example
#         fields = '__all__'
"""
    (app_dir / "serializers.py").write_text(content)


def add_to_installed_apps(name: str) -> None:
    text = SETTINGS_FILE.read_text()
    app_string = f'"apps.{name}"'

    if app_string in text:
        print(f"Приложение 'apps.{name}' уже есть в INSTALLED_APPS — пропускаем.")
        return

    if MARKER not in text:
        print(
            f"Предупреждение: маркер '{MARKER}' не найден в settings.py. "
            "Добавь 'apps.{name}' в INSTALLED_APPS вручную."
        )
        return

    new_text = text.replace(MARKER, f"    {app_string},\n    {MARKER}")
    SETTINGS_FILE.write_text(new_text)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    name = sys.argv[1]
    validate_name(name)

    app_dir = APPS_DIR / name
    check_not_exists(app_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    print(f"Создаю приложение '{name}' в apps/{name}/ ...")
    run_startapp(name, app_dir)
    patch_apps_py(name, app_dir)
    create_urls_py(app_dir)
    create_serializers_py(app_dir)
    add_to_installed_apps(name)

    print(f"\nГотово! Приложение 'apps.{name}' создано.")
    print("\nНе забудь подключить его маршруты в core/urls.py:")
    print(f"    path('api/{name}/', include('apps.{name}.urls')),")


if __name__ == "__main__":
    main()

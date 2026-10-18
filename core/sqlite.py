"""
Поиск без учёта регистра для кириллицы в SQLite.

Встроенный LIKE в SQLite сравнивает без учёта регистра только латиницу: «мука» не находит «Мука».
Django реализует icontains через LIKE, поэтому подменяем функцию like() на Unicode-версию.
В PostgreSQL (ILIKE / UPPER) проблемы нет — подмена действует только для SQLite.
"""

import re
from functools import lru_cache

from django.db.backends.signals import connection_created


@lru_cache(maxsize=1024)
def _compile(pattern: str, escape: str | None) -> re.Pattern:
    parts, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if escape and ch == escape and i + 1 < len(pattern):
            parts.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        parts.append(".*" if ch == "%" else "." if ch == "_" else re.escape(ch))
        i += 1
    return re.compile("^" + "".join(parts) + "$", re.DOTALL | re.IGNORECASE)


def unicode_like(pattern, value, escape=None):
    """SQLite вызывает like(шаблон, значение[, escape]) для «значение LIKE шаблон»."""
    if pattern is None or value is None:
        return None
    return _compile(pattern, escape).match(str(value)) is not None


def _register(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function("like", 2, unicode_like, deterministic=True)
        connection.connection.create_function("like", 3, unicode_like, deterministic=True)


def install():
    connection_created.connect(_register, dispatch_uid="core.sqlite.unicode_like")

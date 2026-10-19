"""
Автоматические записи таймлайна: документ создан, документ сменил статус.

Прежний статус запоминается при загрузке объекта (post_init) — без лишнего запроса перед сохранением.
Изменения через QuerySet.update() сигналов не вызывают и в ленту не попадают.
"""

from django.db.models.signals import post_init, post_save

from core.current_user import get_current_user

from .models import Activity
from .notify import notify
from .registry import TRACKED, model_of

_SEEN = "_activity_status"


def _remember_status(sender, instance, **kwargs):
    # __dict__, а не атрибут: если поле отложено (defer/only), не делаем запрос ради журнала
    setattr(instance, _SEEN, instance.__dict__.get("status"))


def _status_label(instance, code):
    field = instance._meta.get_field("status")
    return dict(field.choices).get(code, code)


def _record(sender, instance, created, raw=False, **kwargs):
    if raw:  # loaddata
        return
    author = get_current_user()
    has_status = hasattr(instance, "status")
    if created:
        Activity.objects.create(
            kind=Activity.Kind.CREATED, target=instance,
            # Вне запроса (seed, команды) автор — тот, кто записан в документе
            author=author or getattr(instance, "created_by", None),
            new_status=instance.status if has_status else "",
        )
    elif has_status:
        old = getattr(instance, _SEEN, None)
        if old is not None and old != instance.status:
            Activity.objects.create(
                kind=Activity.Kind.STATUS, target=instance, author=author,
                old_status=old, new_status=instance.status,
                text=f"{_status_label(instance, old)} → {_status_label(instance, instance.status)}",
            )
    setattr(instance, _SEEN, getattr(instance, "status", None))


def _notify(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        notify(instance)


def connect():
    post_save.connect(_notify, sender=Activity, dispatch_uid="activity-notify")
    for tracked in TRACKED:
        model = model_of(tracked)
        post_init.connect(_remember_status, sender=model, dispatch_uid=f"activity-init-{tracked.model}")
        post_save.connect(_record, sender=model, dispatch_uid=f"activity-save-{tracked.model}")

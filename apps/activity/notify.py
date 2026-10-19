"""
Кому уведомление о новой записи ленты. Каждый получает одно уведомление — по самой сильной причине:

1. упоминание `@логин` в комментарии или сообщении;
2. участник документа — создатель документа и все, кто его комментировал;
3. роль — события, после которых роль должна что-то сделать (таблица ROLE_RULES).

Автор записи себя не уведомляет.
"""

import re
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from apps.accounts.models import Role

from .models import Activity, Notification
from .registry import key_of

MENTION = re.compile(r"(?<![\w@])@([\w.\-]+)")


@dataclass(frozen=True)
class RoleRule:
    target: str  # тип документа: sales.salesorder
    kind: str  # created / status
    status: str | None  # новый статус; None — любой
    roles: tuple[str, ...]
    text: str
    own_department: bool = False  # только начальникам цеха этого задания (и начальнику производства)


ROLE_RULES = [
    RoleRule("sales.salesorder", Activity.Kind.STATUS, "confirmed", (Role.SHOP_HEAD,), "Заказ ждёт производства"),
    RoleRule("sales.salesorder", Activity.Kind.STATUS, "ready", (Role.STOREKEEPER,), "Заказ готов к отгрузке"),
    RoleRule("production.productiontask", Activity.Kind.CREATED, None, (Role.SHOP_HEAD,), "Новое задание цеху",
             own_department=True),
    RoleRule("production.productiontask", Activity.Kind.STATUS, "done", (Role.SALES, Role.STOREKEEPER),
             "Задание выполнено, продукция на складе"),
    RoleRule("sales.shipment", Activity.Kind.CREATED, None, (Role.ACCOUNTANT,), "Отгрузка — выставлен счёт покупателю"),
    RoleRule("purchasing.purchaseorder", Activity.Kind.STATUS, "sent", (Role.ACCOUNTANT,), "Заявка поставщику отправлена"),
    RoleRule("recipes.recipe", Activity.Kind.STATUS, "active", (Role.SHOP_HEAD, Role.TECHNOLOGIST),
             "Новая рецептура введена в действие"),
]


def _mentioned(activity) -> set[int]:
    names = set(MENTION.findall(activity.text))
    if not names:
        return set()
    return set(get_user_model().objects.filter(username__in=names, is_active=True).values_list("pk", flat=True))


def _participants(activity) -> set[int]:
    if not activity.content_type_id:
        return set()
    ids = set(
        Activity.objects.filter(
            content_type_id=activity.content_type_id, object_id=activity.object_id, kind=Activity.Kind.COMMENT,
        ).exclude(author=None).values_list("author_id", flat=True)
    )
    target = activity.target
    if target is not None and getattr(target, "created_by_id", None):
        ids.add(target.created_by_id)
    return ids


def _by_role(activity) -> dict[int, str]:
    if not activity.content_type_id:
        return {}
    from apps.production.permissions import own_department_id

    key = key_of(activity.content_type)
    found: dict[int, str] = {}
    for rule in ROLE_RULES:
        if rule.target != key or rule.kind != activity.kind or (rule.status and rule.status != activity.new_status):
            continue
        users = get_user_model().objects.filter(role__in=rule.roles, is_active=True)
        for user in users:
            if rule.own_department and own_department_id(user) not in (None, activity.target.department_id):
                continue
            found.setdefault(user.pk, rule.text)
    return found


def notify(activity: Activity) -> list[Notification]:
    reasons: dict[int, tuple[str, str]] = {}
    for pk, text in _by_role(activity).items():
        reasons[pk] = (Notification.Reason.ROLE, text)
    for pk in _participants(activity):
        reasons[pk] = (Notification.Reason.PARTICIPANT, "")
    for pk in _mentioned(activity):
        reasons[pk] = (Notification.Reason.MENTION, "")
    reasons.pop(activity.author_id, None)
    return Notification.objects.bulk_create(
        [Notification(recipient_id=pk, activity=activity, reason=reason, text=text) for pk, (reason, text) in reasons.items()],
        ignore_conflicts=True,
    )

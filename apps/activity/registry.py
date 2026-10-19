"""
Какие документы ведут таймлайн: тип (app_label.model) → подпись и маршрут карточки во фронтенде.

Зарплатные документы сюда намеренно не входят: лента общая, а зарплата видна не всем ролям.
"""

from dataclasses import dataclass
from typing import Callable

from django.apps import apps
from django.contrib.contenttypes.models import ContentType


@dataclass(frozen=True)
class Tracked:
    model: str  # "sales.SalesOrder"
    title: str  # «Заказ»
    path: str  # маршрут карточки во фронтенде: /orders
    label: Callable = lambda obj: obj.number or "черновик"


TRACKED = [
    Tracked("sales.SalesOrder", "Заказ", "/orders"),
    Tracked("sales.Shipment", "Накладная", "/shipments"),
    Tracked("production.ProductionTask", "Задание", "/tasks"),
    Tracked("purchasing.PurchaseOrder", "Заявка поставщику", "/purchase-orders"),
    Tracked("purchasing.Receipt", "Приёмка", "/receipts"),
    Tracked("recipes.Recipe", "Рецептура", "/recipes", lambda r: f"«{r.product.name}», версия {r.version}"),
]


def model_of(tracked: Tracked):
    return apps.get_model(tracked.model)


def by_model(model) -> Tracked | None:
    name = f"{model._meta.app_label}.{model.__name__}"
    return next((t for t in TRACKED if t.model.lower() == name.lower()), None)


def by_key(key: str) -> Tracked | None:
    """Ключ из API: «sales.salesorder»."""
    return next((t for t in TRACKED if t.model.lower() == key.lower()), None)


def key_of(content_type: ContentType) -> str:
    return f"{content_type.app_label}.{content_type.model}"


def describe(obj) -> dict:
    """Подпись документа для ленты: «Заказ ЗК-00001» и ссылка на карточку."""
    tracked = by_model(type(obj))
    return {"title": f"{tracked.title} {tracked.label(obj)}", "path": f"{tracked.path}/{obj.pk}"}

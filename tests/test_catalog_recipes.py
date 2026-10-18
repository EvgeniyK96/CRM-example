from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.accounts.models import Role
from apps.catalog.models import Category, Item, ItemKind, Unit
from apps.hr.models import Department
from apps.recipes.models import Recipe

RECIPES = "/api/recipes/"


@pytest.fixture
def cat(db):
    kg = Unit.objects.create(code="кг", name="килограмм")
    pcs = Unit.objects.create(code="шт", name="штука")
    shop = Department.objects.create(name="Пряничный цех", is_production=True)
    office = Department.objects.create(name="Бухгалтерия")
    flour = Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=kg, shelf_life_days=180)
    honey = Item.objects.create(kind=ItemKind.RAW, code="R2", name="Мёд", unit=kg, shelf_life_days=365)
    cake = Item.objects.create(
        kind=ItemKind.PRODUCT, code="P1", name="Пряник", unit=pcs, shelf_life_days=60, department=shop
    )
    return {"kg": kg, "pcs": pcs, "shop": shop, "office": office, "flour": flour, "honey": honey, "cake": cake}


@pytest.fixture
def tech(make_client):
    return make_client(Role.TECHNOLOGIST)


def recipe_payload(cat, **extra):
    data = {
        "product": cat["cake"].id,
        "output_qty": "100",
        "lines": [
            {"ingredient": cat["flour"].id, "quantity": "7", "loss_percent": "2"},
            {"ingredient": cat["honey"].id, "quantity": "1.5", "loss_percent": "0"},
        ],
    }
    data.update(extra)
    return data


def create_recipe(client, cat, **extra):
    r = client.post(RECIPES, recipe_payload(cat, **extra), format="json")
    assert r.status_code == 201, r.data
    return r.data


# --- Каталог ---------------------------------------------------------------


def product_payload(cat, **extra):
    data = {"kind": "product", "code": "P2", "name": "Вафли", "unit": cat["pcs"].id, "shelf_life_days": 90,
            "department": cat["shop"].id}
    data.update(extra)
    return data


def test_technologist_creates_item(tech, cat):
    r = tech.post("/api/catalog/items/", product_payload(cat), format="json")
    assert r.status_code == 201 and r.data["department_name"] == "Пряничный цех"


def test_sales_cannot_create_item(make_client, cat):
    assert make_client(Role.SALES).post("/api/catalog/items/", product_payload(cat), format="json").status_code == 403


@pytest.mark.parametrize(
    "extra, field",
    [
        ({"department": None}, "department"),  # продукту нужен цех
        ({"department": "office"}, "department"),  # подразделение не производственное
        ({"kind": "raw"}, "department"),  # у сырья нет цеха
        ({"category": "raw_cat"}, "category"),  # категория другого типа
    ],
)
def test_item_validation(tech, cat, extra, field):
    raw_cat = Category.objects.create(name="Мука", kind=ItemKind.RAW)
    refs = {"office": cat["office"].id, "raw_cat": raw_cat.id}
    extra = {k: refs.get(v, v) if isinstance(v, str) else v for k, v in extra.items()}
    r = tech.post("/api/catalog/items/", product_payload(cat, **extra), format="json")
    assert r.status_code == 400 and field in r.data


def test_page_size_param(tech, cat):
    assert len(tech.get("/api/catalog/items/?page_size=2").data["results"]) == 2


def test_storekeeper_manages_suppliers(make_client):
    payload = {"name": "ТОО Мука"}
    assert make_client(Role.STOREKEEPER).post("/api/catalog/suppliers/", payload, format="json").status_code == 201
    assert make_client(Role.TECHNOLOGIST).post("/api/catalog/suppliers/", payload, format="json").status_code == 403


# --- Рецептуры -------------------------------------------------------------


def test_create_recipe_draft_v1(tech, cat):
    data = create_recipe(tech, cat)
    assert data["version"] == 1 and data["status"] == "draft" and len(data["lines"]) == 2


def test_recipe_requires_product_and_raw_ingredients(tech, cat):
    r = tech.post(RECIPES, recipe_payload(cat, product=cat["flour"].id), format="json")
    assert r.status_code == 400 and "product" in r.data
    bad_lines = [{"ingredient": cat["cake"].id, "quantity": "1"}]
    r = tech.post(RECIPES, recipe_payload(cat, lines=bad_lines), format="json")
    assert r.status_code == 400 and "lines" in r.data


def test_recipe_rejects_duplicate_ingredient(tech, cat):
    lines = [{"ingredient": cat["flour"].id, "quantity": "1"}, {"ingredient": cat["flour"].id, "quantity": "2"}]
    r = tech.post(RECIPES, recipe_payload(cat, lines=lines), format="json")
    assert r.status_code == 400 and "lines" in r.data


def test_only_technologist_writes_recipes(make_client, cat):
    client = make_client(Role.SHOP_HEAD)
    assert client.get(RECIPES).status_code == 200
    assert client.post(RECIPES, recipe_payload(cat), format="json").status_code == 403


def test_activate_and_versioning(tech, cat):
    v1 = create_recipe(tech, cat)
    assert tech.post(f"{RECIPES}{v1['id']}/activate/").data["status"] == "active"

    v2 = tech.post(f"{RECIPES}{v1['id']}/copy/").data
    assert v2["version"] == 2 and v2["status"] == "draft" and len(v2["lines"]) == 2

    tech.post(f"{RECIPES}{v2['id']}/activate/")
    statuses = dict(Recipe.objects.values_list("version", "status"))
    assert statuses == {1: "archived", 2: "active"}


def test_active_recipe_is_read_only(tech, cat):
    v1 = create_recipe(tech, cat)
    tech.post(f"{RECIPES}{v1['id']}/activate/")
    assert tech.patch(f"{RECIPES}{v1['id']}/", {"output_qty": "50"}, format="json").status_code == 400
    assert tech.delete(f"{RECIPES}{v1['id']}/").status_code == 400
    assert tech.post(f"{RECIPES}{v1['id']}/activate/").status_code == 400


def test_draft_update_replaces_lines(tech, cat):
    v1 = create_recipe(tech, cat)
    lines = [{"ingredient": cat["honey"].id, "quantity": "3"}]
    r = tech.patch(f"{RECIPES}{v1['id']}/", {"lines": lines}, format="json")
    assert r.status_code == 200 and [line["ingredient_name"] for line in r.data["lines"]] == ["Мёд"]


def test_cannot_activate_empty_recipe(tech, cat):
    v1 = create_recipe(tech, cat, lines=[])
    assert tech.post(f"{RECIPES}{v1['id']}/activate/").status_code == 400


def test_calculate_includes_losses(tech, cat):
    v1 = create_recipe(tech, cat)
    r = tech.get(f"{RECIPES}{v1['id']}/calculate/?qty=250")
    need = {line["ingredient_name"]: Decimal(line["quantity"]) for line in r.data["lines"]}
    # мука: 7 кг × 1.02 × 250/100 = 17.85; мёд: 1.5 × 250/100 = 3.75
    assert need == {"Мука": Decimal("17.850"), "Мёд": Decimal("3.750")}
    assert tech.get(f"{RECIPES}{v1['id']}/calculate/?qty=0").status_code == 400


def test_db_allows_single_active_recipe(cat):
    Recipe.objects.create(product=cat["cake"], version=1, output_qty=10, status="active")
    with pytest.raises(IntegrityError):
        Recipe.objects.create(product=cat["cake"], version=2, output_qty=10, status="active")


def test_seed_commands(db):
    from django.core.management import call_command

    call_command("seed_recipes")
    assert Recipe.objects.filter(status="active").count() == Item.objects.filter(kind="product").count() == 9


def test_cyrillic_search_is_case_insensitive(tech, cat):
    """SQLite по умолчанию не сравнивает кириллицу без учёта регистра — core.sqlite это исправляет."""
    names = [r["name"] for r in tech.get("/api/catalog/items/?search=мука").data["results"]]
    assert names == ["Мука"]
    assert tech.get("/api/catalog/items/?search=МЁД").data["count"] == 1
    assert tech.get("/api/catalog/items/?search=r1").data["count"] == 1  # латиница по-прежнему работает

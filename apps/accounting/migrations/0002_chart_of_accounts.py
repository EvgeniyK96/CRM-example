from django.db import migrations

# Данные встроены в миграцию (а не импортированы из chart.py), чтобы она воспроизводилась одинаково всегда
CHART = [
    ("1010", "Денежные средства в кассе", "asset"),
    ("1030", "Денежные средства на текущих банковских счетах", "asset"),
    ("1210", "Краткосрочная дебиторская задолженность покупателей", "asset"),
    ("1310", "Сырьё и материалы", "asset"),
    ("1320", "Готовая продукция", "asset"),
    ("3310", "Краткосрочная кредиторская задолженность поставщикам", "liability"),
    ("3350", "Краткосрочная задолженность по оплате труда", "liability"),
    ("5510", "Нераспределённая прибыль (непокрытый убыток)", "equity"),
    ("6010", "Доход от реализации продукции", "income"),
    ("7010", "Себестоимость реализованной продукции", "expense"),
    ("7210", "Административные расходы", "expense"),
    ("7470", "Прочие расходы (потери, брак, порча)", "expense"),
    ("8110", "Основное производство", "asset"),
]


def create_chart(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    for code, name, type_ in CHART:
        Account.objects.get_or_create(code=code, defaults={"name": name, "type": type_})


class Migration(migrations.Migration):
    dependencies = [("accounting", "0001_initial")]

    operations = [migrations.RunPython(create_chart, migrations.RunPython.noop)]

from django.db import migrations

# Учебные упрощённые ставки по образцу РК (не для реального расчёта)
RATES = [
    # код, название, кто платит, база, %, счёт обязательства
    ("OPV", "ОПВ — обязательные пенсионные взносы", "employee", "gross", "10", "3220"),
    ("VOSMS", "ВОСМС — взносы на медстрахование", "employee", "gross", "2", "3213"),
    ("IPN", "ИПН — подоходный налог", "employee", "taxable", "10", "3120"),
    ("SO", "СО — социальные отчисления", "employer", "gross", "5", "3211"),
    ("OOSMS", "ООСМС — отчисления на медстрахование", "employer", "gross", "3", "3213"),
    ("OPVR", "ОПВР — пенсионные взносы работодателя", "employer", "gross", "2.5", "3220"),
]


def create_rates(apps, schema_editor):
    PayrollRate = apps.get_model("payroll", "PayrollRate")
    for code, name, payer, base, percent, account in RATES:
        PayrollRate.objects.get_or_create(code=code, defaults={
            "name": name, "payer": payer, "base": base, "percent": percent, "account_code": account,
        })


class Migration(migrations.Migration):
    dependencies = [("payroll", "0001_initial")]

    operations = [migrations.RunPython(create_rates, migrations.RunPython.noop)]

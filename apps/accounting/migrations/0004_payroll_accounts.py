from django.db import migrations

ACCOUNTS = [
    ("3120", "Индивидуальный подоходный налог", "liability"),
    ("3211", "Обязательства по социальным отчислениям", "liability"),
    ("3213", "Обязательства по взносам на ОСМС", "liability"),
    ("3220", "Обязательства по пенсионным взносам", "liability"),
    ("7110", "Расходы на оплату труда производства (директ-костинг)", "expense"),
]


def create_accounts(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    for code, name, type_ in ACCOUNTS:
        Account.objects.get_or_create(code=code, defaults={"name": name, "type": type_})


class Migration(migrations.Migration):
    dependencies = [("accounting", "0003_payroll_sources")]

    operations = [migrations.RunPython(create_accounts, migrations.RunPython.noop)]

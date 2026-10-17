from datetime import date

from django.db import migrations

# Нерабочие праздничные дни РК на 2026 год (учебные данные; переносы выходных не учтены)
HOLIDAYS_2026 = [
    (date(2026, 1, 1), "Новый год"),
    (date(2026, 1, 2), "Новый год"),
    (date(2026, 3, 8), "Международный женский день"),
    (date(2026, 3, 21), "Наурыз мейрамы"),
    (date(2026, 3, 22), "Наурыз мейрамы"),
    (date(2026, 3, 23), "Наурыз мейрамы"),
    (date(2026, 5, 1), "Праздник единства народа Казахстана"),
    (date(2026, 5, 7), "День защитника Отечества"),
    (date(2026, 5, 9), "День Победы"),
    (date(2026, 5, 27), "Курбан айт"),
    (date(2026, 7, 6), "День столицы"),
    (date(2026, 8, 30), "День Конституции"),
    (date(2026, 10, 25), "День Республики"),
    (date(2026, 12, 16), "День Независимости"),
]


def forwards(apps, schema_editor):
    Employee = apps.get_model("hr", "Employee")
    HROrder = apps.get_model("hr", "HROrder")
    Holiday = apps.get_model("hr", "Holiday")

    for employee in Employee.objects.select_related("position"):
        if not employee.salary:
            employee.salary = employee.position.base_salary
            employee.save(update_fields=["salary"])
        # Приказ о приёме для уже работающих — чтобы история начиналась с приёма
        if not HROrder.objects.filter(employee=employee, kind="hire").exists():
            order = HROrder.objects.create(
                kind="hire", employee=employee, date=employee.hire_date, to_department_id=employee.department_id,
                to_position_id=employee.position_id, to_salary=employee.salary, reason="Внесено при переходе на учёт приказов",
            )
            order.number = f"ПК-{order.pk:05d}"
            order.save(update_fields=["number"])

    for day, name in HOLIDAYS_2026:
        Holiday.objects.get_or_create(date=day, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("hr", "0002_orders_absences_calendar")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

"""
История для документов, созданных до появления ленты: событие «создан» с датой и автором документа.
Статусы задним числом не восстанавливаются — их истории нет.
"""

from django.db import migrations

MODELS = [
    ("sales", "SalesOrder"),
    ("sales", "Shipment"),
    ("production", "ProductionTask"),
    ("purchasing", "PurchaseOrder"),
    ("purchasing", "Receipt"),
    ("recipes", "Recipe"),
]


def backfill(apps, schema_editor):
    Activity = apps.get_model("activity", "Activity")
    ContentType = apps.get_model("contenttypes", "ContentType")
    for app_label, name in MODELS:
        Model = apps.get_model(app_label, name)
        ct, _ = ContentType.objects.get_or_create(app_label=app_label, model=name.lower())
        has_status = any(f.name == "status" for f in Model._meta.fields)
        for doc in Model.objects.all().only("pk", "created_at", "created_by", *(["status"] if has_status else [])):
            activity = Activity.objects.create(
                kind="created", content_type=ct, object_id=doc.pk, author_id=doc.created_by_id,
                new_status=doc.status if has_status else "",
            )
            # auto_now_add не даёт задать дату при создании
            Activity.objects.filter(pk=activity.pk).update(created_at=doc.created_at)


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0001_initial"),
        ("sales", "0002_shipment"),
        ("production", "0001_initial"),
        ("purchasing", "0002_initial"),
        ("recipes", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]

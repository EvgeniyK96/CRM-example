from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Activity(models.Model):
    """
    Запись «живой ленты»: событие документа (создан, сменил статус), комментарий к нему
    или сообщение в ленту без документа. События пишутся автоматически (signals.py).
    """

    class Kind(models.TextChoices):
        CREATED = "created", "Создан"
        STATUS = "status", "Смена статуса"
        COMMENT = "comment", "Комментарий"
        POST = "post", "Сообщение"

    kind = models.CharField("Вид", max_length=10, choices=Kind.choices)
    content_type = models.ForeignKey(ContentType, verbose_name="Тип документа", on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField("ID документа", null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    text = models.TextField("Текст", blank=True)
    old_status = models.CharField("Был статус", max_length=20, blank=True)
    new_status = models.CharField("Стал статус", max_length=20, blank=True)
    created_at = models.DateTimeField("Когда", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Запись ленты"
        verbose_name_plural = "Живая лента"
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["content_type", "object_id", "-created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.text[:50]}"

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Администратор"
    SALES = "sales", "Менеджер по продажам"
    HR = "hr", "Отдел кадров"
    ACCOUNTANT = "accountant", "Бухгалтерия"
    TECHNOLOGIST = "technologist", "Технолог"
    SHOP_HEAD = "shop_head", "Начальник цеха"
    STOREKEEPER = "storekeeper", "Кладовщик"


class User(AbstractUser):
    role = models.CharField("Роль", max_length=20, choices=Role.choices, default=Role.SALES)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = Role.ADMIN
        super().save(*args, **kwargs)

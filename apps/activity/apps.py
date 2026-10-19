from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = "apps.activity"
    verbose_name = "Живая лента"

    def ready(self):
        from . import signals

        signals.connect()

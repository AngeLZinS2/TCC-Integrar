from django.apps import AppConfig


class AutomationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.automations"
    verbose_name = "Automações"

    def ready(self):
        from . import handlers  # noqa: F401

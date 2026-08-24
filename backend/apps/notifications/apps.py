from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notificações"

    def ready(self):
        # Registra os receivers que geram as notificações automáticas.
        from . import signals  # noqa: F401

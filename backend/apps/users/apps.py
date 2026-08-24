from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"          # label curto para AUTH_USER_MODEL = "users.User"
    verbose_name = "Usuários"

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin do User customizado.
    Substitui os fieldsets padrão do Django para refletir nossos campos
    (email, full_name, role, sector, position).
    """

    list_display = ["email", "full_name", "role", "company", "sector", "position", "is_active", "created_at"]
    list_filter = ["role", "company", "sector", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    ordering = ["full_name"]
    readonly_fields = ["created_at", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Informações pessoais",
            {"fields": ("full_name", "role", "company", "sector", "position")},
        ),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "role",
                    "company",
                    "sector",
                    "position",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

from django.contrib import admin

from .models import ExternalConnection


@admin.register(ExternalConnection)
class ExternalConnectionAdmin(admin.ModelAdmin):
    list_display = ("company", "tipo", "host", "banco", "status", "is_active")
    list_filter = ("tipo", "status", "is_active")
    # A senha cifrada nunca aparece, nem como campo somente-leitura.
    exclude = ("senha_cifrada",)
    readonly_fields = ("status", "ultimo_teste_em", "ultimo_erro")

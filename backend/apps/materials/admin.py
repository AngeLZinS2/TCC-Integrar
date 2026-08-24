from django.contrib import admin

from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "sector", "file_url", "created_at"]
    list_filter = ["company", "sector"]
    search_fields = ["title", "file_url"]
    readonly_fields = ["created_at"]

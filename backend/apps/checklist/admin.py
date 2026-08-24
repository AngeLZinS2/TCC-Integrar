from django.contrib import admin

from .models import ChecklistItem, ChecklistProgress


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "deadline", "sector", "order"]
    list_filter = ["company", "deadline", "sector"]
    search_fields = ["title"]
    ordering = ["deadline", "order"]


@admin.register(ChecklistProgress)
class ChecklistProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "item", "completed", "completed_at"]
    list_filter = ["completed", "item__deadline", "item__sector"]
    search_fields = ["user__email", "user__full_name", "item__title"]
    readonly_fields = ["completed_at"]

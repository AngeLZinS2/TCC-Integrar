from django.contrib import admin

from .models import Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "city", "state", "status")
    list_filter = ("company", "status", "state")
    search_fields = ("name", "code", "city")

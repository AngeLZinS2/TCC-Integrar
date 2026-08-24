from django.contrib import admin

from .models import Position, Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "description_preview", "position_count"]
    list_filter = ["company"]
    search_fields = ["name"]

    @admin.display(description="Descrição")
    def description_preview(self, obj: Sector) -> str:
        return (obj.description[:60] + "…") if len(obj.description) > 60 else obj.description

    @admin.display(description="Nº de cargos")
    def position_count(self, obj: Sector) -> int:
        return obj.positions.count()


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["name", "sector"]
    list_filter = ["sector"]
    search_fields = ["name", "sector__name"]
    autocomplete_fields = ["sector"]

from django.contrib import admin

from .models import Event, EventAttendance


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "start_at", "status", "organizer")
    list_filter = ("company", "status", "start_at")
    search_fields = ("title", "description", "location")


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "responded_at")
    list_filter = ("status",)

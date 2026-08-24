from django.contrib import admin
from .models import Announcement, AnnouncementRead

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'is_urgent', 'created_at')
    list_filter = ('company', 'is_urgent')
    search_fields = ('title', 'content')
    filter_horizontal = ('target_sectors', 'target_positions')

@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'user', 'read_at')
    list_filter = ('announcement__company',)

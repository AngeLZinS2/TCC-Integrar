from django.contrib import admin
from .models import HRRequest, RequestHistory, RequestComment

@admin.register(HRRequest)
class HRRequestAdmin(admin.ModelAdmin):
    list_display = ('number', 'company', 'requester', 'category', 'status', 'priority', 'created_at')
    list_filter = ('company', 'status', 'priority', 'category')
    search_fields = ('number', 'subject', 'requester__email')
    readonly_fields = ('number', 'created_at', 'updated_at')

@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('request', 'actor', 'action_type', 'created_at')
    list_filter = ('action_type',)
    search_fields = ('request__number', 'actor__email')

@admin.register(RequestComment)
class RequestCommentAdmin(admin.ModelAdmin):
    list_display = ('request', 'author', 'created_at')
    search_fields = ('request__number', 'author__email')

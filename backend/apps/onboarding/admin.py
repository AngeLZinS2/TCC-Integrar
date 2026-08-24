from django.contrib import admin

from .models import OnboardingTask, OnboardingTemplate, TemplateTask


class TemplateTaskInline(admin.TabularInline):
    model = TemplateTask
    extra = 1


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "sector", "position", "is_active")
    list_filter = ("company", "is_active")
    inlines = [TemplateTaskInline]


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "assigned_to", "due_date", "status")
    list_filter = ("company", "status", "priority")
    search_fields = ("title", "employee__full_name")

from django.contrib import admin

from .models import AutomationAction, AutomationCondition, AutomationRule, AutomationRun


class ConditionInline(admin.TabularInline):
    model = AutomationCondition
    extra = 0


class ActionInline(admin.TabularInline):
    model = AutomationAction
    extra = 1


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "trigger_event", "is_active")
    list_filter = ("company", "trigger_event", "is_active")
    inlines = [ConditionInline, ActionInline]


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = ("rule", "status", "subject_label", "created_at")
    list_filter = ("company", "status")
    readonly_fields = ("rule", "company", "status", "subject_label", "detail", "created_at")

from django.contrib import admin

from .models import Content, Course, CourseProgress


class ContentInline(admin.TabularInline):
    model = Content
    extra = 1
    fields = ["order", "type", "file_url"]
    ordering = ["order"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "sector", "position", "order", "content_count"]
    list_filter = ["company", "sector", "position"]
    search_fields = ["title", "description"]
    inlines = [ContentInline]
    ordering = ["order", "title"]

    @admin.display(description="Nº de conteúdos")
    def content_count(self, obj: Course) -> int:
        return obj.contents.count()


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ["course", "order", "type", "file_url"]
    list_filter = ["type", "course__sector", "course"]
    search_fields = ["course__title", "file_url"]
    ordering = ["course", "order"]


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "status", "completed_at"]
    list_filter = ["status", "course__sector", "course"]
    search_fields = ["user__email", "user__full_name", "course__title"]
    readonly_fields = ["completed_at"]

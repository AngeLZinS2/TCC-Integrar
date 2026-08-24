from django.contrib import admin
from .models import DocumentCategory, Document, DocumentVersion, DocumentAcceptance

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    list_filter = ('company',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'company', 'is_required')
    list_filter = ('company', 'is_required', 'category')
    search_fields = ('title',)

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'is_active', 'published_at')
    list_filter = ('document__company', 'is_active')

@admin.register(DocumentAcceptance)
class DocumentAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('document_version', 'user', 'accepted_at', 'ip_address')
    list_filter = ('document_version__document__company',)

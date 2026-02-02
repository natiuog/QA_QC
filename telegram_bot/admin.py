from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'document_type', 'project_name', 'user_name', 
        'file_name', 'uploaded_at', 'is_replied', 'scan_copy_present'
    ]
    list_filter = ['document_type', 'is_replied', 'scan_copy_present', 'uploaded_at']
    search_fields = ['project_name', 'user_name', 'file_name', 'remarks']
    readonly_fields = ['uploaded_at']
    fieldsets = (
        ('Document Information', {
            'fields': ('document_type', 'project_name', 'user_name', 'file_name')
        }),
        ('Status', {
            'fields': ('is_replied', 'scan_copy_present', 'remarks')
        }),
        ('Additional Info', {
            'fields': ('comments', 'file_path', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-uploaded_at']

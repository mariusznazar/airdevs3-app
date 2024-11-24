from django.contrib import admin
from .models import FileAnalysis

@admin.register(FileAnalysis)
class FileAnalysisAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_type', 'category', 'created_at', 'updated_at')
    list_filter = ('file_type', 'category')
    search_fields = ('file_name', 'content')
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return False 
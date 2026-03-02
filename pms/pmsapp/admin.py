from django.contrib import admin
from .models import UpgradeLog


@admin.register(UpgradeLog)
class UpgradeLogAdmin(admin.ModelAdmin):
    list_display = (
        'log_id', 'user', 'upload_time', 'patch_file_name', 'upgrade_file_name',
        'status', 'notes', 'action_source', 'ip_address', 'upgrade_version'
    )
    search_fields = (
        'patch_file_name', 'upgrade_file_name', 'status', 'action_source', 'upgrade_version'
    )
    list_filter = ('status', 'upload_time', 'action_source')
    readonly_fields = ('upload_time',)

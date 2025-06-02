from django.contrib import admin
from .models import TelegramChannel, TelegramMessage, DeletedMessage, ArchivedGithubUrl, CrawlerLog, CrawlerSettings, CrawlerStatus, MessageKeyword

@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_name', 'channel_id', 'username', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['channel_name', 'username', 'channel_id']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'channel', 'classification', 'timestamp', 'created_at']
    list_filter = ['classification', 'timestamp', 'channel']
    search_fields = ['message_text', 'message_id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['channel']
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel')

@admin.register(DeletedMessage)
class DeletedMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'channel', 'reason', 'deleted_at']
    list_filter = ['reason', 'deleted_at', 'channel']
    search_fields = ['message_id']
    readonly_fields = ['deleted_at']
    raw_id_fields = ['channel']

@admin.register(ArchivedGithubUrl)
class ArchivedGithubUrlAdmin(admin.ModelAdmin):
    list_display = ['url', 'message', 'is_archived', 'processed_at']
    list_filter = ['is_archived', 'processed_at']
    search_fields = ['url', 'archive_url']
    readonly_fields = ['processed_at']
    raw_id_fields = ['message']

@admin.register(CrawlerLog)
class CrawlerLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'level', 'module', 'message_short']
    list_filter = ['level', 'module', 'timestamp']
    search_fields = ['message', 'module']
    readonly_fields = ['timestamp', 'level', 'module', 'message']
    ordering = ['-timestamp']  # Latest logs on top
    list_per_page = 50  # 50 logs per page
    
    def message_short(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_short.short_description = "Message (Short)"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(CrawlerSettings)
class CrawlerSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.name in ['TELEGRAM_API_HASH']:
            form.base_fields['value'].widget.attrs['type'] = 'password'
        return form

@admin.register(CrawlerStatus)
class CrawlerStatusAdmin(admin.ModelAdmin):
    list_display = ['status', 'is_running', 'process_id', 'started_at', 'messages_processed']
    list_filter = ['status', 'is_running', 'started_at']
    readonly_fields = ['started_at', 'stopped_at']
    
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False

@admin.register(MessageKeyword)
class MessageKeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'keyword_type', 'case_sensitive', 'is_active', 'updated_at']
    list_filter = ['keyword_type', 'case_sensitive', 'is_active', 'created_at']
    search_fields = ['keyword', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active', 'case_sensitive']
    ordering = ['keyword_type', 'keyword']
    actions = ['make_active', 'make_inactive', 'populate_defaults']
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} keywords have been activated.')
    make_active.short_description = "Activate selected keywords"
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} keywords have been deactivated.')
    make_inactive.short_description = "Deactivate selected keywords"
    
    def populate_defaults(self, request, queryset):
        from .models import MessageKeyword
        MessageKeyword.populate_default_keywords()
        self.message_user(request, 'Default keywords added.')
    populate_defaults.short_description = "Add default keywords"

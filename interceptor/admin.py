from django.contrib import admin
from .models import AutoSendMessageSetting

@admin.register(AutoSendMessageSetting)
class AutoSendMessageSettingAdmin(admin.ModelAdmin):
    list_display = ('is_enabled', 'auto_sent_count')
    list_editable = ('is_enabled',)
    list_display_links = ('auto_sent_count',)  # Сделать поле 'auto_sent_count' ссылкой

# Если вы не хотите, чтобы какие-либо поля были ссылками:
# list_display_links = (None,)

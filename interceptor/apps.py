from django.apps import AppConfig
import asyncio


class InterceptorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interceptor'
    
    def ready(self):
        from .telethon_client import start_client
        # Стартуем клиент Telethon при старте Django
        asyncio.get_event_loop().create_task(start_client())
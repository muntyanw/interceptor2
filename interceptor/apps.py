from django.apps import AppConfig
import asyncio

class InterceptorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interceptor'

    def ready(self):
        from .telethon_client import start_client  # Клиент Telethon

        loop = asyncio.get_event_loop()

        # Запускаем задачи независимо от того, активен ли event loop
        loop.create_task(start_client())  # Запуск клиента Telethon как асинхронной задачи

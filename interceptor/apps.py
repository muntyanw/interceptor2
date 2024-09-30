from django.apps import AppConfig
import asyncio
import sys

class InterceptorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interceptor'

    def ready(self):
        # Отключаем загрузку сессий при выполнении миграций
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            from .telethon_client import start_client  # Клиент Telethon

            loop = asyncio.get_event_loop()

            # Запускаем задачи независимо от того, активен ли event loop
            loop.create_task(start_client())  # Запуск клиента Telethon как асинхронной задачи

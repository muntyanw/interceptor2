import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from  interceptor.routing import websocket_urlpatterns
import logging


logger = logging.getLogger(__name__)

logger.info("[asgi] DJANGO_SETTINGS_MODULE := telegram_interceptor.settings")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_interceptor.settings')

# Инициализация Django перед использованием любых моделей или компонентов
logger.info("[asgi] django.setup()")
django.setup()

logger.info(f"[asgi] interceptor.routing.websocket_urlpatterns = {websocket_urlpatterns}")
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .telethon_client import send_message_to_channels
import os
import base64

logger = logging.getLogger(__name__)


class TelegramConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("[TelegramConsumer] Установка WebSocket соединения")
        await self.channel_layer.group_add("telegram_group", self.channel_name)
        await self.accept()
        logger.info("[TelegramConsumer] WebSocket соединение установлено")

    async def disconnect(self, close_code):
        logger.info(
            f"[TelegramConsumer] Отключение WebSocket соединения: код {close_code}"
        )
        await self.channel_layer.group_discard("telegram_group", self.channel_name)


    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_text = data.get("new_text", "")
            new_files = data.get("new_files", [])
            existing_files = data.get("existing_files", [])

            files = []

            # Обработка новых файлов и их сохранение на диск
            for file in new_files:
                file_name = file.get("name")
                file_data = file.get("data").split(",")[
                    1
                ]  # Убираем префикс 'data:image/jpeg;base64,'
                file_bytes = base64.b64decode(file_data)

                # Сохраняем файл на диск
                folder_temp_path = "/tmp"
                if not os.path.exists(folder_temp_path):
                    os.makedirs(folder_temp_path)
                    print(f"Папка {folder_temp_path} создана.")
                else:
                    print(f"Папка {folder_temp_path} уже существует.")
                file_path = os.path.join(folder_temp_path, file_name)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                files.append(file_path)

            # Обработка существующих файлов
            for file_url in existing_files:
                files.append(file_url)

            await send_message_to_channels(message_text, files)
        except json.JSONDecodeError:
            # Логирование ошибки или отправка сообщения об ошибке
            logger.info("[TelegramConsumer] Invalid JSON received")
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON received'
            }))

    async def send_new_message(self, event):
        # pdb.set_trace()
        message = event["message"]
        files = event.get("files", [])
        logger.info(
            f"[TelegramConsumer] Отправка нового сообщения клиенту через WebSocket: {message}, файлы: {files}"
        )
        await self.send(text_data=json.dumps({"message": message, "files": files}))

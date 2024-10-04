from asgiref.sync import sync_to_async
import asyncio
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
from . import channels
from . import utils
import os
from channels.layers import get_channel_layer  # для работы с WebSocket
from .logger import logger
from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel, DocumentAttributeVideo
from collections import deque, defaultdict
import hashlib
import time

handler_registered = False

# Ограничение на количество хранимых сообщений
MAX_SENT_MESSAGES = 30
sent_messages = deque(maxlen=MAX_SENT_MESSAGES)  # Очередь с ограничением размера

# Хранилище для временного сохранения частей сообщений
message_parts = defaultdict(lambda: {'files': [], 'text': None, 'sender_name': None, 'start_time': None, 'video_params': None})
COLLECT_TIMEOUT = 2  # Таймаут ожидания всех частей сообщения

client = None
client_bot = None

# Очередь для хранения входящих сообщений
message_queue = deque()
# Флаг для отслеживания обработки
is_processing = False

download_directory = "storage/"

async def createClients():
    global client
    global client_bot
    logger.info("[createClients] Проверяем законекчен ли клиент.")
    if client is None or not client.is_connected():
        logger.info("[createClients] Создаем клиент.")
        client = TelegramClient(channels.name_session_client, channels.api_id, channels.api_hash,
                                connection_retries=10,  # Количество попыток переподключения
                                timeout=60  # Тайм-аут ожидания в секундах
                            )
        await client.connect()
    else:
        logger.info("[createClients] Клиент есть и законекчен.")

    logger.info("[createClients] Проверяем законекчен ли бот клиент.")
    if client_bot is None or not client_bot.is_connected():   
        logger.info("[createClients] Создаем бот клиент.")
        client_bot = TelegramClient(
                channels.name_session_bot,
                channels.api_id,
                channels.api_hash,
                connection_retries=10,  # Количество попыток переподключения
                timeout=60  # Тайм-аут ожидания в секундах
            )
        await client_bot.connect()
    else:
        logger.info("[createClients] Клиент есть и законекчен.")

async def start_client_bot():
    global client_bot
    try:
        logger.info("[start_client] Старт Клієнт бот")
        await client_bot.start(bot_token=channels.bot_token)  # Не забываем использовать await
        
        logger.info("[start_client] Клієнт бот успішно стартанув")
        
        # Получаем информацию о боте
        await utils.get_bot_info(client_bot)

    except Exception as e:
        logger.error(f"Ошибка при запуске клиента: {e}")

async def send_message_to_channels(channels_to_send, message_text, files, reply_to_msg_id=None, buttons=None, video_params=None):
    logger.info(f"[send_message_to_channels] Попытка отправки сообщения")
    await asyncio.sleep(1)
    # Создаем уникальный идентификатор сообщения/файла
    unique_id = message_text if message_text else ""
    if files:
        for file in files:
            unique_id += utils.hash_file(file)  # Добавляем хэш файла к идентификатору
    if unique_id in sent_messages:
        logger.warning("[send_message_to_channels] Сообщение или файл уже были отправлены, пропуск отправки.")
        return
    sent_messages.append(unique_id)  # Добавление уникального идентификатора в очередь
    for channel in channels_to_send:
        logger.info(f"[send_message_to_channels] Старт отправки для канала channel = {channel}")
        try:
            if files:
                if video_params:  # Если это видео, отправляем с параметрами
                    logger.info(f"[send_message_to_channels] Отправка видео с параметрами в канал: {channel}")
                    entity = await client_bot.get_entity(channel)
                    await client_bot.send_file(
                        entity,
                        files,
                        caption=message_text,
                        album=True,
                        reply_to=reply_to_msg_id,
                        buttons=buttons,
                        attributes=[DocumentAttributeVideo(
                            duration=video_params['duration'],
                            w=video_params['width'],
                            h=video_params['height'],
                            supports_streaming=video_params['supports_streaming']
                        )]
                    )
                else:    
                    logger.info(f"[send_message_to_channels] Отправка файла клиєнтом в канал: {channel}, файлы: {files}")
                    entity = await client.get_entity(channel)
                    await client.send_file(entity, files, caption=message_text, album=True, reply_to=reply_to_msg_id)
            else:
                if buttons:
                    logger.info(f"[send_message_to_channels] Отправка сообщения в канал ботом: {channel}, buttons: {buttons}")
                    entity = await client_bot.get_entity(channel)
                    await client_bot.send_message(entity, message_text, reply_to=reply_to_msg_id, buttons=buttons) #
                else:
                    logger.info(f"[send_message_to_channels] Отправка сообщения в канал клієнтом: {channel}")
                    entity = await client.get_entity(channel)
                    await client.send_message(entity, message_text, reply_to=reply_to_msg_id)
                    
        except FloodWaitError as e:
            logger.warning(f"[send_message_to_channels] FloodWaitError: {e}. Ожидание {e.seconds} секунд.")
            await asyncio.sleep(e.seconds)  # Ожидание перед повторной отправкой
        except Exception as e:
            logger.error(f"[send_message_to_channels] Ошибка при отправке сообщения: {e}")
    logger.info("[send_message_to_channels] Завершение отправки сообщений и файлов.")
    
async def process_message(chat_id, reply_to_msg_id=None):
    from .models import AutoSendMessageSetting
    """Обрабатывает сообщение из `message_parts` после таймаута."""
    message_data = message_parts[chat_id]
    files = message_data['files']
    message_text = message_data['text'] or ""
    sender_name = message_data['sender_name']
    buttons = message_data['buttons']
    video_params = message_data['video_params']
    
    logger.info(f"[process_message] Сообщение из канала {chat_id}: {message_text}, Отправитель: {sender_name}, Файлы: {files}, Видео параметры: {video_params}")
    try:
        get_first_setting = sync_to_async(AutoSendMessageSetting.objects.first)
        setting = await get_first_setting()
    except Exception as e:
        logger.error(f"Failed to get setting: {e}")
    setting = None  # Или обработайте ошибку соответствующим образом
    
    if setting and setting.is_enabled:
        logger.info(f"[process_message] setting.is_enabled = true Отправка сообщения без модерирования!")
        await send_message_to_channels(channels_to_send, message_text, files, reply_to_msg_id, buttons, video_params)
    else:
        modified_message, moderation_if_image, auto_moderation_and_send_text_message, channels_to_send = utils.replace_words(message_text, chat_id)
        logger.info(f"[process_message] moderation_if_image: {moderation_if_image}, file_paths: {files}, moderation_if_image and file_paths: {moderation_if_image and files}, modified_message: {modified_message}")
        if (moderation_if_image and files) or not auto_moderation_and_send_text_message:
            logger.info(f"[process_message] Отправка сообщения через WebSocket на фронт человеку")
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                "telegram_group",
                {
                    "type": "send_new_message",
                    "message": modified_message,
                    "files": files,
                },
            )
        else:
            logger.info(f"[process_message] Автоматическое перенаправление в канал")
            await send_message_to_channels(
                channels_to_send, 
                modified_message, 
                utils.replace_words_in_images(files, channels.replacements_in_images), 
                reply_to_msg_id,
                utils.update_buttons(buttons, channels.replacements_in_buttons),
                video_params
            )
    
    # Очищаем временное хранилище для текущего сообщения
    try:
        del message_parts[chat_id]
    except KeyError:
        logger.error(f"KeyError: Не удалось удалить части сообщения для {chat_id}, возможно, они уже были удалены.")

# Функция для добавления сообщений в очередь
async def add_to_queue(event):
    logger.info(f"[add_to_queue] Додаємо месседж до черги. event.id: {event.id}")
    message_queue.append(event)
    await process_queue()

# Обработка одного сообщения
async def process_single_message(event):
    chat_id = utils.extract_original_id(event.chat_id)
    sender = await event.get_sender()
    sender_name = getattr(sender, 'first_name', 'Unknown') if hasattr(sender, 'first_name') else getattr(sender, 'title', 'Unknown')
    
    reply_to_msg_id = None

    buttons = await event.get_buttons()

    if buttons:
        logger.info(f"[handler] Получены кнопки")
        buttons = utils.formatted_buttons(buttons)
            
    if event.is_reply:
        original_message = await event.get_reply_message()
        logger.info(f"[handler] Сообщение от {chat_id} является ответом на сообщение ID {original_message.id}.")
        # Set the reply_to_msg_id to the ID of the original message
        reply_to_msg_id = original_message.id
        
        
    message = event.message

    if message.media:
        file_path = await message.download_media(file=download_directory)
        
        video_params = None
        
        # Проверяем, является ли медиа видео и сохраняем параметры
        if isinstance(message.media, types.MessageMediaDocument):
            for attribute in message.media.document.attributes:
                if isinstance(attribute, DocumentAttributeVideo):
                    logger.info(f"[handler] Видео обнаружено: длительность {attribute.duration}, разрешение {attribute.w}x{attribute.h}")
                    video_params = {
                        'duration': attribute.duration,
                        'width': attribute.w,
                        'height': attribute.h,
                        'supports_streaming': attribute.supports_streaming
                    }
        
        if message_parts[chat_id]['start_time'] is None:
            # Запоминаем время первого сообщения с файлом
            message_parts[chat_id]['start_time'] = time.time()
            message_parts[chat_id]['files'].append(file_path)
            message_parts[chat_id]['text'] = message.text
            message_parts[chat_id]['buttons'] = buttons
            message_parts[chat_id]['video_params'] = video_params
            logger.info(f"[handler] Первое сообщение с файлом получено от {chat_id}. Запускаем таймер.")
            await asyncio.sleep(COLLECT_TIMEOUT)
            await process_message(chat_id, reply_to_msg_id)
        else:
            logger.info(f"[handler] Дополнительный файл получен от {chat_id}. Добавляем к уже полученным файлам.")
            message_parts[chat_id]['files'].append(file_path)
            if buttons:
                message_parts[chat_id]['buttons'].append(buttons)
            if message.text:
                message_parts[chat_id]['text'] += message.text
            if video_params:
                message_parts[chat_id]['video_params'] = video_params
    else:
        if message.text:
            if message_parts[chat_id]['start_time']: #если ожидание сборщика
                message_parts[chat_id]['start_time'] = time.time()
                await asyncio.sleep(COLLECT_TIMEOUT)  #подождем когда уйдет прошлое
            message_parts[chat_id]['text'] = message.text
            message_parts[chat_id]['buttons'] = buttons
            # Обработка сообщения сразу если есть текст
            logger.info(f"[handler] Текстовое сообщение получено от {chat_id}. Немедленная обработка.")
            await process_message(chat_id, reply_to_msg_id)
    
# Функция для обработки сообщений из очереди
async def process_queue():
    global is_processing

    if is_processing:
        logger.info(f"[process_queue] Вже йде обробка. Виходим.")
        return

    is_processing = True
    logger.info(f"[process_queue] Початок обробкі чергі.")

    tasks = []
    while message_queue:
        event = message_queue.popleft()
        logger.info(f"[process_queue] Наступний меседж із чергі. event.id:{event.id}")

        # Запускаем обработку каждого сообщения как отдельную задачу
        tasks.append(asyncio.create_task(process_single_message(event)))
            
    # Убираем флаг после завершения обработки
    is_processing = False
    
async def start_client():
    global handler_registered
    global download_directory
    
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    max_retries = 5
    delay = 10  # Задержка между попытками в секундах

    await createClients()
    
    for attempt in range(max_retries):
        try:
            if not handler_registered:
                logger.info(f"[start_client] Регистрируем обработчик")
                await client.connect()
                if not await client.is_user_authorized():
                    logger.info("[start_client] Клиент не авторизован, завершаем процесс")
                    return
                logger.info("[start_client] Клиент Telethon успешно подключен и авторизован")
                
                await start_client_bot()
                
                chat_ids = list(channels.channels_to_listen.keys())

                @client.on(events.NewMessage(chats=chat_ids))
                async def handler(event):
                    # Добавляем сообщение в очередь для обработки
                    await add_to_queue(event)
                    
                logger.info("[start_client] Обработчики NewMessage зарегистрированы для всех каналов")
                handler_registered = True
                
                try:
                    await client.run_until_disconnected()
                except Exception as e:
                    logger.info(f"[start_client] Произошла ошибка: {e}")
                
                break  # Выход из цикла попыток при успешном подключении
            else:
                logger.info("[start_client] Обработчики NewMessage уже были зарегестрированы")

        except Exception as e:
                        logger.error(f"[start_client] Ошибка при подключении клиента Telethon: {e}")
                        if attempt < max_retries - 1:
                            logger.info(f"Попытка повторного подключения через {delay} секунд... ({attempt + 1}/{max_retries})")
                            time.sleep(delay)
                        else:
                            logger.error("Превышено максимальное количество попыток подключения.")
                            raise

async def main():
    logger.info("[main] Запуск основного процесса")
    await start_client()

if __name__ == "__main__":
    asyncio.run(main())
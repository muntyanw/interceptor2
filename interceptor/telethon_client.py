from asgiref.sync import sync_to_async
import asyncio
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
from . import ses
from . import channels
from . import utils
import os
from channels.layers import get_channel_layer  # для работы с WebSocket
from .logger import logger
from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel
from collections import deque, defaultdict
import hashlib
import time
from telethon.tl.custom import Button

handler_registered = False

# Ограничение на количество хранимых сообщений
MAX_SENT_MESSAGES = 30
sent_messages = deque(maxlen=MAX_SENT_MESSAGES)  # Очередь с ограничением размера

# Хранилище для временного сохранения частей сообщений
message_parts = defaultdict(lambda: {'files': [], 'text': None, 'sender_name': None, 'start_time': None})
COLLECT_TIMEOUT = 2  # Таймаут ожидания всех частей сообщения

# Создание клиента
client = TelegramClient(ses.session, channels.api_id, channels.api_hash,
                        connection_retries=10,  # Количество попыток переподключения
                        timeout=60  # Тайм-аут ожидания в секундах
                       )

async def send_message_to_channels(message_text, files, reply_to_msg_id=None, buttons=None):
    logger.info(f"[send_message_to_channels] Попытка отправки сообщения: {message_text} с файлами: {files}")
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
    for channel in channels.channels_to_send:
        entity = await client.get_entity(PeerChannel(channel))
        try:
            if files:
                logger.info(f"[send_message_to_channels] Отправка файла в канал: {channel}, файлы: {files}, buttons: {buttons}")
                await client.send_file(entity, files, caption=message_text, album=True, reply_to=reply_to_msg_id, buttons=buttons)
            else:
                logger.info(f"[send_message_to_channels] Отправка сообщения в канал: {channel}, buttons: {buttons}")
                await client.send_message(entity, message_text, reply_to=reply_to_msg_id, buttons=buttons)
        except FloodWaitError as e:
            logger.warning(f"[send_message_to_channels] FloodWaitError: {e}. Ожидание {e.seconds} секунд.")
            await asyncio.sleep(e.seconds)  # Ожидание перед повторной отправкой
        except Exception as e:
            logger.error(f"[send_message_to_channels] Ошибка при отправке сообщения: {e}")
    logger.info("[send_message_to_channels] Завершение отправки сообщений и файлов.")
    

async def process_message(chat_id, reply_to_msg_id=None, buttons=None):
    from .models import AutoSendMessageSetting
    """Обрабатывает сообщение из `message_parts` после таймаута."""
    message_data = message_parts[chat_id]
    files = message_data['files']
    message_text = message_data['text'] or ""
    sender_name = message_data['sender_name']
    logger.info(f"[process_message] Сообщение из канала {chat_id}: {message_text}, Отправитель: {sender_name}, Файлы: {files}")
    try:
        get_first_setting = sync_to_async(AutoSendMessageSetting.objects.first)
        setting = await get_first_setting()
    except Exception as e:
        logger.error(f"Failed to get setting: {e}")
    setting = None  # Или обработайте ошибку соответствующим образом

    if setting and setting.is_enabled:
        await send_message_to_channels(message_text, files, reply_to_msg_id, buttons)
    else:
        modified_message, moderation_if_image, auto_moderation_and_send_text_message = utils.replace_words(message_text, chat_id)
        logger.error(f"[process_message] moderation_if_image: {moderation_if_image}, file_paths: {files}, moderation_if_image and file_paths: {moderation_if_image and files}, modified_message: {modified_message}")

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
                modified_message, 
                utils.replace_words_in_images(files, channels.replacements_in_images), 
                reply_to_msg_id,
                utils.update_buttons(buttons, channels.replacements_in_buttons)
            )
    
    # Очищаем временное хранилище для текущего сообщения
    try:
        del message_parts[chat_id]
    except KeyError:
        logger.error(f"KeyError: Не удалось удалить части сообщения для {chat_id}, возможно, они уже были удалены.")

async def start_client():
    global handler_registered
    download_directory = "storage/"
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    max_retries = 5
    delay = 10  # Задержка между попытками в секундах
    for attempt in range(max_retries):
        try:
            if not handler_registered:
                logger.info(f"[start_client] Регистрируем обработчик")
                #await client.start(bot_token=channels.bot_token)
                await client.connect()
                if not await client.is_user_authorized():
                    logger.info("[start_client] Клиент не авторизован, завершаем процесс")
                    return
                ses.save_session(ses.session_name, client.session.save())
                logger.info("[start_client] Клиент Telethon успешно подключен и авторизован")
                chat_ids = list(channels.channels_to_listen.keys())

                @client.on(events.NewMessage(chats=chat_ids))
                async def handler(event):
                    chat_id = utils.extract_original_id(event.chat_id)
                    sender = await event.get_sender()
                    sender_name = getattr(sender, 'first_name', 'Unknown') if hasattr(sender, 'first_name') else getattr(sender, 'title', 'Unknown')
                    
                    reply_to_msg_id = None
                                       
                    #buttons = [
                    #    [Button.url('Google', 'https://www.google.com')],
                    #    [Button.url('YouTube', 'https://www.youtube.com')]
                    #]
                    #buttons=[[Button.inline('Left'), Button.inline('Right')], [Button.url('Check this site!', 'https://example.com')]]
                    buttons = None
                    
                    if event.is_reply:
                        original_message = await event.get_reply_message()
                        logger.info(f"[handler] Сообщение от {chat_id} является ответом на сообщение ID {original_message.id}.")
                        # Set the reply_to_msg_id to the ID of the original message
                        reply_to_msg_id = original_message.id
                        
                     # Проверка на наличие инлайн-кнопок в сообщении
                    message = event.message
                    if message.reply_markup:  # Проверяем наличие кнопок
                        if isinstance(message.reply_markup, types.ReplyInlineMarkup):
                            print("Inline кнопки:")
                            for row in message.reply_markup.rows:
                                for button in row.buttons:
                                    print(f"Текст кнопки: {button.text}")
                        elif isinstance(message.reply_markup, types.ReplyKeyboardMarkup):
                            print("Обычные кнопки:")
                            for row in message.reply_markup.rows:
                                for button in row.buttons:
                                    print(f"Текст кнопки: {button.text}")

                    if message.media:
                        file_path = await message.download_media(file=download_directory)
                        if message_parts[chat_id]['start_time'] is None:
                            # Запоминаем время первого сообщения с файлом
                            message_parts[chat_id]['start_time'] = time.time()
                            message_parts[chat_id]['files'].append(file_path)
                            message_parts[chat_id]['text'] = message.text
                            logger.info(f"[handler] Первое сообщение с файлом получено от {chat_id}. Запускаем таймер.")
                            # Запускаем таймер для обработки сообщения после COLLECT_TIMEOUT
                            await asyncio.sleep(COLLECT_TIMEOUT)
                            await process_message(chat_id, reply_to_msg_id, buttons)
                        else:
                            logger.info(f"[handler] Дополнительный файл получен от {chat_id}. Добавляем к уже полученным файлам.")
                            message_parts[chat_id]['files'].append(file_path)
                            if message.text:
                                message_parts[chat_id]['text'] += message.text
                    else:
                        if message.text:
                            if message_parts[chat_id]['start_time']:#если ожиндания сборщика
                                message_parts[chat_id]['start_time'] = time.time()
                                await asyncio.sleep(COLLECT_TIMEOUT)  #подождем когда уйдет прошлое
                            message_parts[chat_id]['text'] = message.text
                            # Обработка сообщения сразу если есть текст
                            logger.info(f"[handler] Текстовое сообщение получено от {chat_id}. Немедленная обработка.")
                            await process_message(chat_id, reply_to_msg_id, buttons)
                            return

                logger.info("[start_client] Обработчики NewMessage зарегистрированы для всех каналов")
                handler_registered = True
                
                try:
                    await client.run_until_disconnected()
                except Exception as e:
                    logger.info(f"[un_until_disconnected] Произошла ошибка: {e}")
                
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


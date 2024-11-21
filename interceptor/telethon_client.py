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
from telethon.tl.types import PeerChannel
from collections import deque, defaultdict
import hashlib
import time
from telethon.tl.custom import Button
from telethon.tl.custom.messagebutton import MessageButton
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename
import pprint
from django.conf import settings
from pydub.utils import mediainfo
from telethon.tl.types import DocumentAttributeAudio


MAX_CAPTION_LENGTH = 1024

# Инициализация pprint
pp = pprint.PrettyPrinter(indent=2)

handler_registered = False

# Ограничение на количество хранимых сообщений
MAX_SENT_MESSAGES = 30
sent_messages = deque(maxlen=MAX_SENT_MESSAGES)  # Очередь с ограничением размера
eventIds = deque(maxlen=MAX_SENT_MESSAGES)

# Хранилище для временного сохранения частей сообщений
message_parts = defaultdict(lambda: {'files': [], 'text': None, 'sender_name': None, 'start_time': None})
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
    
    try:
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
        
    except Exception as e:
        logger.error(f"[createClients] Ошибка при попытке создания клиента {e}")
        #logger.error(f"[createClients] Удаляем ссесию")
        #utils.removeFilesSessions(settings)

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

async def send_message_to_channels(channels_to_send, message_text, files, reply_to_msg_id=None, buttons=None, attributes=None, messageIds=None, isTgsticker=False, isVoice=False):
    logger.info(f"[send_message_to_channels] Попытка отправки сообщения")
    # Создаем уникальный идентификатор сообщения/файла
    unique_id = message_text if message_text else ""
    if files:
        for file in files:
            if file:  # Проверка, что файл не None
                try:
                    unique_id += utils.hash_file(file)  # Добавляем хэш файла к идентификатору
                except Exception as e:
                    logger.error(f"[send_message_to_channels] Ошибка при вычислении хэша файла {file}: {e}")
            else:
                logger.warning(f"[send_message_to_channels] Файл имеет значение None и не будет обработан.")
    if unique_id in sent_messages:
        logger.warning(f"[send_message_to_channels] Сообщение или файл уже были отправлены, пропуск отправки.")
        return
    sent_messages.append(unique_id)  # Добавление уникального идентификатора в очередь
    
    for channel in channels_to_send:
        logger.info(f"[send_message_to_channels][channel:{channel}] Старт отправки для канала channel = {channel}, Ids сообщений {messageIds}")
        try:
            if files:
                if isTgsticker or isVoice:
                    logger.info(f"[send_message_to_channels][channel:{channel}] Отправка файла клиентом в канал: {channel}, файлы: {files}, buttons: {buttons}")
                    entity = await client.get_entity(channel)
                    await client.send_file(entity, files, caption=message_text, album=True, reply_to=reply_to_msg_id, buttons=buttons, attributes=attributes)
                else:
                    logger.info(f"[send_message_to_channels][channel:{channel}] Отправка файла ботом в канал: {channel}, файлы: {files}, buttons: {buttons}")
                    entity = await client_bot.get_entity(channel)
                    await client_bot.send_file(entity, files, caption=message_text, album=True, reply_to=reply_to_msg_id, buttons=buttons, attributes=attributes) #
            else:
                if buttons:
                    logger.info(f"[send_message_to_channels][channel:{channel}] Отправка сообщения в канал ботом: {channel}, buttons: {buttons}")
                    entity = await client_bot.get_entity(channel)
                    await client_bot.send_message(entity, message_text, reply_to=reply_to_msg_id, buttons=buttons, attributes=attributes) #
                else:
                    logger.info(f"[send_message_to_channels][channel:{channel}] Отправка сообщения в канал клієнтом: {channel}")
                    entity = await client.get_entity(channel)
                    await client.send_message(entity, message_text, reply_to=reply_to_msg_id, attributes=attributes)
                    
        except FloodWaitError as e:
            logger.warning(f"[send_message_to_channels][channel:{channel}] FloodWaitError: {e}. Ожидание {e.seconds} секунд.")
            await asyncio.sleep(e.seconds)  # Ожидание перед повторной отправкой
        except Exception as e:
            logger.error(f"[send_message_to_channels][channel:{channel}] Ошибка при отправке сообщения: {e}")
    logger.info(f"[send_message_to_channels][channel:{channel}] Завершение отправки сообщений и файлов.")
    
async def process_message(chat_id, reply_to_msg_id=None):
    from .models import AutoSendMessageSetting
    logger.info(f"[process_message][chat_id:{chat_id}] Обрабатывает сообщение из `message_parts`.")
    message_data = message_parts[chat_id]
    files = message_data['files']
    message_text = message_data['text'] or ""
    
    if 'webpage' in message_parts[chat_id]:
        logger.info(f"[process_message][chat_id:{chat_id}] Найдена приставка webpage:{message_data['webpage']} Добавляем ее к сообщению.!")
        message_text += message_data['webpage']
    
    sender_name = message_data['sender_name']
    buttons = message_data.get('buttons', None)
    attributes = message_data.get('attributes', None) 
    isTgsticker = message_data.get('isTgsticker', None)
    messageIds = message_data.get('messageIds', None)
    isVoice = message_data.get('isVoice', None)
    
    logger.info(f"[process_message][chat_id:{chat_id}] Сообщение из канала {chat_id}: {message_text}, Отправитель: {sender_name}, Файлы: {files}")
    
    logger.info(f"[process_message][chat_id:{chat_id}] Ids сообщений {messageIds}.")
    
    try:
        get_first_setting = sync_to_async(AutoSendMessageSetting.objects.first)
        setting = await get_first_setting()
    except Exception as e:
        logger.error(f"Failed to get setting: {e}")
    setting = None  # Или обработайте ошибку соответствующим образом
    
    if setting and setting.is_enabled:
        logger.info(f"[process_message][chat_id:{chat_id}] setting.is_enabled = true Отправка сообщения без модерирования!")
        await send_message_to_channels(channels_to_send, message_text, files, reply_to_msg_id, buttons, attributes, messageIds, isTgsticker, isVoice)
    else:
        modified_message, moderation_if_image, auto_moderation_and_send_text_message, channels_to_send = utils.replace_words(message_text, chat_id)
        logger.info(f"[process_message][chat_id:{chat_id}] moderation_if_image: {moderation_if_image}, file_paths: {files}, moderation_if_image and file_paths: {moderation_if_image and files}, modified_message: {modified_message}")
        if (moderation_if_image and files) or not auto_moderation_and_send_text_message:
            logger.info(f"[process_message][chat_id:{chat_id}] Отправка сообщения через WebSocket на фронт человеку")
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
            logger.info(f"[process_message][chat_id:{chat_id}] Автоматическое перенаправление в канал")
            await send_message_to_channels(
                channels_to_send, 
                modified_message, 
                utils.replace_words_in_images(files, channels.replacements_in_images), 
                reply_to_msg_id,
                utils.update_buttons(buttons, channels.replacements_in_buttons),
                attributes,
                messageIds,
                isTgsticker,
                isVoice
            )
    
    # Очищаем временное хранилище для текущего сообщения
    try:
        del message_parts[chat_id]
    except KeyError:
        logger.error(f"[process_message][chat_id:{chat_id}] KeyError: Не удалось удалить части сообщения для {chat_id}, возможно, они уже были удалены.")

# Функция для добавления сообщений в очередь
async def add_to_queue(event):
   
   if event.id in eventIds:
        logger.warning("[add_to_queue] Этот евент уже был добавлен в очередь, пропускаем.")
        return
   eventIds.append(event.id)

   logger.info(f"[add_to_queue] Додаємо месседж до черги. event.id: {event.id}")
   message_queue.append(event)
   await process_queue()

# Обработка одного сообщения
async def process_single_message(event):
    
   global download_directory
    
   chat_id = utils.extract_original_id(event.chat_id)
   sender = await event.get_sender()
   sender_name = getattr(sender, 'first_name', 'Unknown') if hasattr(sender, 'first_name') else getattr(sender, 'title', 'Unknown')
   message = event.message
   
   reply_to_msg_id = None
   buttons = await event.get_buttons()
   
   if 'attributes' not in message_parts[chat_id]:
      message_parts[chat_id]['attributes'] = []
   
   if 'messageIds' not in message_parts[chat_id]:
      message_parts[chat_id]['messageIds'] = []
      
   message_parts[chat_id]['isTgsticker'] = None
   message_parts[chat_id]['isVoice'] = None
   
   message_parts[chat_id]['messageIds'].append(message.id)
      

   if buttons:
      logger.info(f"[process_single_message][chat_id:{chat_id}] Получены кнопки")
      buttons = utils.formatted_buttons(buttons)
         
   if event.is_reply:
      original_message = await event.get_reply_message()
      logger.info(f"[process_single_message][chat_id:{chat_id}] Сообщение от {chat_id} является ответом на сообщение ID {original_message.id}.")
      # Set the reply_to_msg_id to the ID of the original message
      reply_to_msg_id = original_message.id
   
   file_path = None
   
   logger.info(f"[process_single_message][chat_id:{chat_id}] Ищем медиа")
   if message.media:
        file_path = await message.download_media(file=download_directory)
        logger.info(f"[process_single_message][chat_id:{chat_id}] Проверяем тип медиа")
        media_type = type(message.media)
        logger.info(f"[process_single_message][chat_id:{chat_id}] Тип медиа: {media_type}")
        
        if isinstance(message.media, types.MessageMediaDocument):
            logger.info(f"[process_single_message][chat_id:{chat_id}] Медиа является документом, аудио  или видео,  добавляем в message_parts[chat_id]['attributes']")
                        
            document = message.media.document

            if utils.is_video_file(file_path):
                logger.info(f"[process_single_message][chat_id:{chat_id}] Это видео")
                width, height, duration, fps = utils.get_video_dimensions_cv2(file_path)
                logger.info(f"[process_single_message][chat_id:{chat_id}] Получили атрибуты видео width:{width} , height:{height}, duration:{duration}")
                 # Создание атрибутов для видео
                video_attributes = [DocumentAttributeVideo(
                                        duration=duration,
                                        w=width,
                                        h=height,
                                        supports_streaming=True
                                   )]
                message_parts[chat_id].setdefault('attributes', []).append(video_attributes)


            if utils.is_sticker(file_path) or (document.mime_type == 'application/x-tgsticker' and document.attributes):
                logger.info(f"[process_single_message][chat_id:{chat_id}] Это стикер")
                if any(hasattr(attr, 'type') and attr.type == 'animation' for attr in document.attributes):
                    logger.info(f"[process_single_message][chat_id:{chat_id}] Это анимированный стикер")
                    message_parts[chat_id]['isTgsticker'] = True
                message_parts[chat_id].setdefault('attributes', []).append(message.media.document.attributes)
                
                    
            if utils.has_file_with_extensions([file_path], ['.ogg', '.oga']):
                logger.info(f"[process_single_message][chat_id:{chat_id}] Это войс")
                message_parts[chat_id]['isVoice'] = True
                output_file = utils.change_file_extension(file_path, 'mp3')
                utils.convert_oga_to_mp3(file_path, output_file)
                file_path = output_file

                info = mediainfo(file_path)
                duration = int(float(info['duration']))

                audio_attributes = [DocumentAttributeAudio(
                                duration=duration,
                                voice=True, 
                        
                             )]
                
                message_parts[chat_id].setdefault('attributes', []).append(audio_attributes)

            logger.info(f"[process_single_message][chat_id:{chat_id}] Атрибуты attributes:")
            utils.log_attributes(message_parts[chat_id]['attributes'])
            
        elif isinstance(message.media, types.MessageMediaPhoto):
            logger.info(f"[process_single_message][chat_id:{chat_id}] Медиа является фотографией, добавляем None в message_parts[chat_id]['attributes']")
            message_parts[chat_id].setdefault('attributes', []).append(None)
            
        elif isinstance(message.media, types.MessageMediaWebPage):
            # Извлекаем ссылку из объекта MessageMediaWebPage
            web_page = message.media.webpage
            if isinstance(web_page, types.WebPage):
                url = web_page.url
                message_parts[chat_id]['webpage'] =f"\{url}"
                message_parts[chat_id].setdefault('attributes', []).append(None)
            
        else:
            logger.info(f"[process_single_message][chat_id:{chat_id}] Неизвестный тип медиа")
            message_parts[chat_id].setdefault('attributes', []).append(message.media)
        
                
        if message_parts[chat_id]['start_time'] is None:
            # Запоминаем время первого сообщения с файлом
            message_parts[chat_id]['start_time'] = time.time()
            message_parts[chat_id]['files'].append(file_path)
            message_parts[chat_id]['text'] = message.text
            message_parts[chat_id]['buttons'] = buttons
            
            if not message_parts[chat_id].get('isTgsticker', False):
                logger.info(f"[process_single_message][chat_id:{chat_id}] Первое сообщение с файлом получено от {chat_id}. Запускаем таймер.")
                await asyncio.sleep(COLLECT_TIMEOUT)
            else:
                logger.info(f"[process_single_message][chat_id:{chat_id}] Это стикер отправляем сразу.")
                
            await process_message(chat_id, reply_to_msg_id)
        else:
            logger.info(f"[process_single_message][chat_id:{chat_id}] Дополнительный файл получен от {chat_id}. Добавляем к уже полученным файлам.")
            message_parts[chat_id]['files'].append(file_path)
            if buttons:
                message_parts[chat_id]['buttons'].append(buttons)
            if message.text:
                message_parts[chat_id]['text'] += message.text

        if message_parts[chat_id].get('text') and len(message_parts[chat_id]['text']) > MAX_CAPTION_LENGTH:
                message_parts[chat_id]['text'] = message_parts[chat_id]['text'][:MAX_CAPTION_LENGTH]

        message_parts[chat_id]['text'] = utils.add_closing_bracket_if_needed(message_parts[chat_id]['text'])

   else:
       
        logger.info(f"[process_single_message][chat_id:{chat_id}] Нет медиа вложений")
        
        if message.text:
            if message_parts[chat_id]['start_time']: #если ожиндания сборщика
                message_parts[chat_id]['start_time'] = time.time()
                await asyncio.sleep(COLLECT_TIMEOUT)  #подождем когда уйдет прошлое
            message_parts[chat_id]['text'] = message.text
            message_parts[chat_id]['buttons'] = buttons
            # Обработка сообщения сразу если есть текст
            logger.info(f"[process_single_message][chat_id:{chat_id}] Текстовое сообщение получено от {chat_id}. Немедленная обработка.")
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
                     #logger.info("[start_client] Клиент не авторизован, идем на следующую попытку")
                     #time.sleep(delay)
                     #continue
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


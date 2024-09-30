import os
from django.shortcuts import render, get_object_or_404, redirect
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from . import channels
from . import utils 
from .logger import logger
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.http import JsonResponse
from .models import AutoSendMessageSetting, TelegramMessage
from django.conf import settings
from telethon.sessions import SQLiteSession
from .telethon_client import client, start_client
import asyncio
from django.http import HttpResponse


# View для работы с сообщениями и их пересылки
async def message_list_and_edit(request, edit_pk=None):
    logger.info("[message_list_and_edit] View для работы с сообщениями и их пересылки.")
    telethon_client_task_running = cache.get('telethon_client_task_running')
    
    logger.info("[message_list_and_edit] Перевірка client.connect")
    if not await client.is_user_authorized() or not telethon_client_task_running:
        return redirect("/")

    # Получение списка сообщений и редактируемого сообщения асинхронно
    messages = await sync_to_async(list)(TelegramMessage.objects.all())
    edit_message = None
    if edit_pk:
        edit_message = await sync_to_async(get_object_or_404)(TelegramMessage, pk=edit_pk)

    if request.method == "POST" and edit_message:
        edit_message.edited_text = request.POST.get("text")
        await sync_to_async(edit_message.save)()
        return redirect("message_list_and_edit")

    setting = await sync_to_async(AutoSendMessageSetting.objects.first)()
    port = os.getenv('PORT', '101')
    return await sync_to_async(render)(
        request,
        "message_list_and_edit.html",
        {
            "messages": messages,
            "edit_message": edit_message,
            "setting": setting,
            "port": port
        },
    )

# Логика отправки сообщений
def send_message(request, pk, chat_id):
    message = get_object_or_404(TelegramMessage, pk=pk)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        client.send_message(chat_id, message.edited_text or message.text)
    )
    if request.is_ajax():
        return JsonResponse({"status": "sent"})
    return redirect("message_list_and_edit")

# Удаление файла
def remove_file(request, pk, file_index):
    message = get_object_or_404(TelegramMessage, pk=pk)
    message.files.pop(file_index)
    message.save()
    return redirect("message_list_and_edit", edit_pk=pk)

# Получение списка диалогов
async def fetch_dialogs(client):
    async with client:
        await client.start()
        dialogs = await client.get_dialogs()
        contacts_and_channels = []
        for dialog in dialogs:
            entity = dialog.entity
            contacts_and_channels.append({
                'id': entity.id,
                'name': getattr(entity, 'title', None) or entity.first_name or entity.username,
                'type': 'channel' if getattr(entity, 'megagroup', False) or getattr(entity, 'broadcast', False) else 'contact'
            })
        return contacts_and_channels

# Вьюха для получения контактов и каналов
async def get_contacts_and_channels(request):
    logger.info("[get_contacts_and_channels] Получен запрос на получение контактов и каналов.")
    
    try:
        dialogs = await client.get_dialogs()
        contacts_and_channels = [{'name': d.name, 'id': d.id} for d in dialogs]
        
        logger.info("[get_contacts_and_channels] Успешно получены контакты и каналы.")
        return render(request, 'contacts_and_channels.html', {
            'contacts_and_channels': contacts_and_channels
        })

    except RuntimeError as e:
        logger.error(f"[get_contacts_and_channels] Ошибка выполнения: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

    except Exception as e:
        logger.error(f"[get_contacts_and_channels] Непредвиденная ошибка: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    
    
# Запуск клиента
async def start_client_view(request):
    logger.info("[start_client_view] Запуск клиента для авторизации.")
    if client:    
        try:
            logger.info("[start_client_view] Попытка подключения клиента.")
            await client.connect()

            # Проверка, авторизован ли клиент
            if not await client.is_user_authorized():
                logger.warning("[start_client_view] Клиент не авторизован, перенаправляем на страницу авторизации.")
                return redirect("telegram_auth")
            else:
                cache.set('telethon_client_task_running', True)
                logger.info("[start_client_view] Установлен флаг telethon_client_task_running в кэш.")
                # Перенаправление к списку сообщений
                return redirect("message_list_and_edit")

        except errors.SessionPasswordNeededError:
            logger.warning("[start_client_view] Требуется двухфакторная аутентификация, перенаправляем.")
            return redirect("two_factor_auth")

        except Exception as e:
            logger.error(f"[start_client_view] Ошибка при запуске клиента: {str(e)}")
            return redirect("error_page")

    else:
        logger.warning(f"[start_client_view] Client не створений.")
        return redirect("telegram_auth")

# Асинхронная функция для проверки авторизации
async def check_authorization(client):
    await client.connect()
    return await client.is_user_authorized()

async def telegram_auth(request):
    logger.info("[telegram_auth] Запрос на авторизацию получен.")
    
    if request.method == "POST":
        phone = request.POST.get("phone")
        code = request.POST.get("code")
        logger.info(f"[telegram_auth] Телефон: {phone}, Код: {code}")

        # Файл для хранения сессии
        session_web_file = utils.get_session_web_file_path(request, settings)

        if phone and not code:
            try:
                # Проверка на подключение
                if not client.is_connected():
                    logger.warning("[telegram_auth] Клиент был отключен, переподключаемся...")
                    await client.connect()

                # Отправляем запрос на получение кода
                result = await client.send_code_request(phone)
                logger.info(f"[telegram_auth] Код авторизации отправлен на номер: {phone}")

                # Сохраняем phone_code_hash в сессии Django
                await sync_to_async(request.session.__setitem__)("phone_code_hash", result.phone_code_hash)
                logger.info(f"[telegram_auth] Сохранен phone_code_hash в сессию: {result.phone_code_hash}")

                return render(request, "auth.html", {"phone": phone, "step": "code"})

            except errors.FloodWaitError as e:
                wait_time = e.seconds
                logger.error(f"[telegram_auth] FloodWaitError: нужно подождать {wait_time} секунд.")
                return render(request, "auth.html", {"error": f"Подождите {wait_time // 60} минут", "step": "phone"})

            except errors.AuthRestartError:
                logger.warning("[telegram_auth] AuthRestartError: Перезапуск процесса авторизации.")
                await client.disconnect()
                return redirect("telegram_auth")

            except Exception as e:
                logger.error(f"[telegram_auth] Error while requesting code: {str(e)}")
                return render(request, "auth.html", {"error": str(e), "step": "phone"})

        elif phone and code:
            try:
                # Создаем клиента с StringSession
                await client.connect()
                logger.info("[telegram_auth] Клиент Telethon подключен для авторизации с кодом.")

                # Получаем phone_code_hash из сессии Django
                phone_code_hash = await sync_to_async(request.session.get)("phone_code_hash")
                logger.info(f"[telegram_auth] Используем phone_code_hash: {phone_code_hash} для телефона: {phone}")

                if not phone_code_hash:
                    raise ValueError("Missing phone_code_hash")

                # Завершаем авторизацию
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                logger.info("[telegram_auth] Успешная авторизация в Telegram.")

                # Очищаем данные из сессии Django
                await sync_to_async(request.session.__delitem__)("phone_code_hash")
                logger.info("[telegram_auth] Очищен phone_code_hash из сессии Django.")

                return redirect("message_list_and_edit")

            except errors.PhoneCodeExpiredError:
                logger.error("[telegram_auth] Код подтверждения истек.")
                return render(request, "auth.html", {"error": "The confirmation code has expired. Please request a new one.", "phone": phone, "step": "phone"})

            except errors.PhoneCodeInvalidError:
                logger.error("[telegram_auth] Введен неверный код подтверждения.")
                return render(request, "auth.html", {"error": "Invalid code. Please try again.", "phone": phone, "step": "code"})

            except errors.SessionPasswordNeededError:
                logger.error("[telegram_auth] Требуется двухфакторная аутентификация.")
                return render(request, "auth.html", {"error": "Two-step verification required. Please enter your password.", "phone": phone, "step": "password"})

            except Exception as e:
                logger.error(f"[telegram_auth] Ошибка во время авторизации: {str(e)}")
                return render(request, "auth.html", {"error": str(e), "step": "phone"})

    logger.info("[telegram_auth] Запрос завершен, возвращаем страницу авторизации.")
    return render(request, "auth.html", {"step": "phone"})

def restart_telethon_client():
    subprocess.Popen(
        ["python3", os.path.join(os.path.dirname(__file__), "telethon_client.py")]
    )

def update_auto_send_setting(request):
    if request.method == "POST":
        setting = AutoSendMessageSetting.objects.first()
        if not setting:
            setting = AutoSendMessageSetting()
        setting.is_enabled = 'is_enabled' in request.POST
        setting.save()
        logger.info(f"[update_auto_send_setting] Настройки обновлены: {setting.is_enabled}")
    return redirect('message_list_and_edit')

def logout_view(request):
    if request.method == 'POST':
        try:
            utils.remove_file(channels.name_session_client)
            logger.info("[logout_view] Клиентская сессия удалена.")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"[logout_view] Ошибка при удалении сессии: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

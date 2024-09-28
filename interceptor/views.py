from django.shortcuts import render, get_object_or_404, redirect

from .models import TelegramMessage

from telethon import TelegramClient, errors

from django.conf import settings

from django.http import JsonResponse

from telethon.sessions import StringSession

from . import ses

from . import channels

from . import telethon_client

import subprocess

import asyncio

from django.utils import timezone

from telethon.errors import FloodWaitError

from asgiref.sync import sync_to_async

from django.core.cache import cache

from .logger import logger

from .models import AutoSendMessageSetting

from django.shortcuts import redirect

import os
from . import channels





# View для работы с сообщениями и их пересылки

 

async def message_list_and_edit(request, edit_pk=None):

    logger.info("[message_list_and_edit] View для работы с сообщениями и их пересылки.")

    session_name = ses.session_name

    session_string = ses.load_session(session_name)

    telethon_client_task_running = cache.get('telethon_client_task_running')



    client = TelegramClient(StringSession(session_string), channels.api_id, channels.api_hash)

    await client.connect()

    logger.info("[message_list_and_edit] client.connect")

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





def remove_file(request, pk, file_index):

    message = get_object_or_404(TelegramMessage, pk=pk)

    message.files.pop(file_index)

    message.save()

    return redirect("message_list_and_edit", edit_pk=pk)



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



def get_contacts_and_channels(request):

    session_string = ses.load_session(ses.session_name)

    

    # Создание нового цикла событий для асинхронной операции

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    

    try:

        client = TelegramClient(StringSession(session_string), channels.api_id, channels.api_hash)

        # Используем sync_to_async для асинхронной функции с созданным циклом событий

        contacts_and_channels = loop.run_until_complete(fetch_dialogs(client))

    finally:

        # Закрытие и удаление цикла событий после завершения работы

        loop.close()



    return render(request, 'contacts_and_channels.html', {

        'contacts_and_channels': contacts_and_channels

    })

    

     

async def start_client_view(request):

    session_name = ses.session_name

    session_string = ses.load_session(session_name)



    if session_string:

        client = TelegramClient(StringSession(session_string), channels.api_id, channels.api_hash)



        try:

            await client.connect()

            if not await client.is_user_authorized():

                return redirect("telegram_auth")



            telethon_client_task = asyncio.create_task(telethon_client.main())

            

            cache.set('telethon_client_task_running', True)

    

            return redirect("message_list_and_edit")

        except errors.SessionPasswordNeededError:

            return redirect("two_factor_auth")

        except Exception as e:

            logger.error(f"Exception during client start: {str(e)}")

            return redirect("error_page")

    else:

        return redirect("telegram_auth")





# Асинхронная функция для проверки авторизации

async def check_authorization(client):

    await client.connect()

    return await client.is_user_authorized()





async def telegram_auth(request):

    if request.method == "POST":

        phone = request.POST.get("phone")

        code = request.POST.get("code")



        if phone and not code:

            try:

                # Создаем и подключаем клиента

                client = TelegramClient(StringSession(), channels.api_id, channels.api_hash)

                await client.connect()



                # Сохраняем сессию после подключения

                await sync_to_async(ses.save_session)(

                    ses.session_name, client.session.save()

                )



                # Отправляем запрос на получение кода

                result = await client.send_code_request(phone)



                # Сохраняем phone_code_hash в сессии

                await sync_to_async(request.session.__setitem__)(

                    "phone_code_hash", result.phone_code_hash

                )

                await sync_to_async(request.session.__setitem__)(

                    "session_string", client.session.save()

                )



                logger.info(f"Received phone_code_hash: {result.phone_code_hash}")

                return render(request, "auth.html", {"phone": phone, "step": "code"})



            except errors.FloodWaitError as e:

                wait_time = e.seconds

                logger.error(

                    f"FloodWaitError: нужно подождать {wait_time} секунд перед повторной отправкой запроса."

                )

                return render(

                    request,

                    "auth.html",

                    {

                        "error": f"Превышен лимит запросов. Подождите {wait_time // 60} минут перед следующей попыткой.",

                        "step": "phone",

                    },

                )



            except Exception as e:

                logger.error(f"Error while requesting code: {str(e)}")

                return render(request, "auth.html", {"error": str(e), "step": "phone"})



        elif phone and code:

            try:

                # Подключаемся с использованием сохраненной сессии

                session_string = await sync_to_async(request.session.get)(

                    "session_string"

                )

                client = TelegramClient(

                    StringSession(session_string), channels.api_id, channels.api_hash

                )

                await client.connect()



                # Получаем phone_code_hash из сессии

                phone_code_hash = await sync_to_async(request.session.get)(

                    "phone_code_hash"

                )

                logger.info(

                    f"Using phone_code_hash: {phone_code_hash} for phone: {phone}"

                )



                if not phone_code_hash:

                    raise ValueError("Missing phone_code_hash")



                # Завершаем авторизацию

                await client.sign_in(

                    phone=phone, code=code, phone_code_hash=phone_code_hash

                )



                # Сохраняем сессию после успешного входа

                await sync_to_async(ses.save_session)(

                    ses.session_name, client.session.save()

                )



                # Удаляем phone_code_hash и сессию из Django сессии

                await sync_to_async(request.session.__delitem__)("phone_code_hash")

                await sync_to_async(request.session.__delitem__)("session_string")



                return redirect("message_list_and_edit")



            except errors.PhoneCodeExpiredError:

                logger.error("The confirmation code has expired.")

                return render(

                    request,

                    "auth.html",

                    {

                        "error": "The confirmation code has expired. Please request a new one.",

                        "phone": phone,

                        "step": "phone",

                    },

                )



            except errors.PhoneCodeInvalidError:

                logger.error("Invalid confirmation code.")

                return render(

                    request,

                    "auth.html",

                    {

                        "error": "Invalid code. Please try again.",

                        "phone": phone,

                        "step": "code",

                    },

                )



            except errors.SessionPasswordNeededError:

                logger.error("Two-step verification required.")

                return render(

                    request,

                    "auth.html",

                    {

                        "error": "Two-step verification required. Please enter your password.",

                        "phone": phone,

                        "step": "password",

                    },

                )



            except Exception as e:

                logger.error(f"Error during sign in: {str(e)}")

                return render(request, "auth.html", {"error": str(e), "step": "phone"})



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

    return redirect('message_list_and_edit')



def logout_view(request):

    if request.method == 'POST':

        session_name = 'intercept_session'  # The session name you want to remove

        try:

            ses.remove_session(session_name)  # Call the remove_session method

            return JsonResponse({'status': 'success'})

        except Exception as e:

            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
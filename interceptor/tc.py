from telethon import TelegramClient, Button, events

client = TelegramClient("sessionBot87-_M", '22900607', '2101d7377e8f53d4d356ba1485d79eeb',
                        connection_retries=10,  # Количество попыток переподключения
                        timeout=60  # Тайм-аут ожидания в секундах
                       ).start(bot_token='7658487162:AAEmSzNUCZ2caOp2rxuo6DeL8Vfcu-aehaA')

async def get_bot_info():
    # Fetch the bot's info
    me = await client.get_me()
    print(f"Bot's Name: {me.username}")

async def sendMessage():
    buttons = [
        [Button.url('Google', 'https://google.com')],
        [Button.inline('Click me', b'1')]
    ]
    
    # Попробуем получить сущность пользователя по его ID
    try:
        entity = await client.get_entity(-1002204843457)  # Получаем сущность пользователя
        await client.send_message(entity, 'click me', buttons=buttons)
    except ValueError as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

@client.on(events.NewMessage(pattern="/options"))
async def handler(event):
    markup = client.build_reply_markup(Button.inline('hi'))
    await client.send_message(event.chat_id, 'click me', buttons=markup)

if __name__ == "__main__":
    client.start()  # Запуск клиента
    client.loop.run_until_complete(get_bot_info())
    print("Client sending messages...")
    client.loop.run_until_complete(sendMessage())
    print("Client started and listening for messages...")
    client.run_until_disconnected()  # Ожидание сообщений

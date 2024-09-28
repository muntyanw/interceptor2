from telethon import TelegramClient, Button, events 
from . import channels


client = TelegramClient("sessionTC", channels.api_id, channels.api_hash,
                        connection_retries=10,  # Количество попыток переподключения
                        timeout=60  # Тайм-аут ожидания в секундах
                       )

@client.on(events.NewMessage(pattern="/options"))
async def handler(event):

    keyboard = [
        [  
            Button.inline("First option", b"1"), 
            Button.inline("Second option", b"2")
        ],
        [
            Button.inline("Third option", b"3"), 
            Button.inline("Fourth option", b"4")
        ],
        [
            Button.inline("Fifth option", b"5")
        ]
    ]

    await client.send_message(event.chat_id, "Choose an option:", buttons=keyboard)
    
    
if __name__ == "__main__":
    client.start()  # Запуск клиента

    print("Client started and listening for messages...")
    client.run_until_disconnected()  # Ожидание сообщений

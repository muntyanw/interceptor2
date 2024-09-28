import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)

import signal

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"Команда /start получена от пользователя {user.first_name} ({user.id}) в чате {chat_id}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="Привет! Бот запущен. Нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Нажми меня", callback_data='button_pressed')]
            ])
        )
        logger.info(f"Сообщение с кнопкой отправлено в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик любого сообщения"""
    try:
        if update.message:
            message_text = update.message.text
            chat_id = update.effective_chat.id
            user = update.effective_user
            logger.info(f"Получено сообщение от пользователя {user.first_name} ({user.id}) в чате {chat_id}: {message_text}")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Вы отправили: {message_text}"
            )
            logger.info(f"Ответ на сообщение успешно отправлен в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике handle_message: {e}")

# Обработчик нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на инлайн-кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        logger.info(f"Пользователь {user.first_name} ({user.id}) нажал кнопку с данными: {query.data}")

        if query.data == 'button_pressed':
            await query.edit_message_text(text="Вы нажали кнопку!")
            logger.info(f"Сообщение обновлено после нажатия кнопки в чате {query.message.chat_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике button_handler: {e}")

async def main():
    """Главная функция, инициализирующая и запускающая бота"""
    logger.info("Инициализация приложения Telegram бота")
    application = ApplicationBuilder().token('7905362232:AAHV2il7ogCFpRLDmM92pLhHYXBsIf87-_M').build()

    # Обработчик команды /start
    logger.info("Регистрация обработчика команды /start")
    application.add_handler(CommandHandler('start', start))

    # Обработчик текстовых сообщений
    logger.info("Регистрация обработчика сообщений")
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    application.add_handler(message_handler)

    # Обработчик нажатий на инлайн-кнопки
    logger.info("Регистрация обработчика нажатий на кнопки")
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск бота
    logger.info("Запуск бота")
    await application.initialize()

    # Получаем текущий цикл событий
    loop = asyncio.get_running_loop()

    # Запускаем приложение в цикле событий
    await application.start()
    logger.info("Бот запущен и готов к работе")

    # Используем событие для ожидания завершения
    stop_event = asyncio.Event()

    # Определяем функцию для обработки сигналов остановки
    def handle_stop_signals(*args):
        logger.info("Получен сигнал остановки")
        stop_event.set()

    # Регистрируем обработчики сигналов остановки
    loop.add_signal_handler(signal.SIGINT, handle_stop_signals)
    loop.add_signal_handler(signal.SIGTERM, handle_stop_signals)

    # Ожидаем события остановки
    await stop_event.wait()

    # Останавливаем бота
    logger.info("Остановка бота")
    await application.stop()
    await application.shutdown()
    logger.info("Бот успешно остановлен")

if __name__ == "__main__":
    try:
        logger.info("Запуск основного цикла событий")
        # Получаем текущий цикл событий или создаем новый
        loop = asyncio.get_event_loop()
        # Проверяем, запущен ли цикл событий
        if not loop.is_running():
            loop.run_until_complete(main())
        else:
            # Если цикл уже запущен, создаем задачу и запускаем цикл
            loop.create_task(main())
            loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Приложение остановлено вручную")
    except Exception as e:
        logger.error(f"Ошибка в основном блоке: {e}")

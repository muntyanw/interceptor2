import logging

# Настройка базового логгера
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений с временем
    datefmt='%Y-%m-%d %H:%M:%S',  # Формат времени (опционально)
    handlers=[
        logging.FileHandler("log.log"),  # Запись логов в файл
        logging.StreamHandler()  # Вывод логов в консоль
    ]
)

# Получение логгера
logger = logging.getLogger(__name__)


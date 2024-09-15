
import cv2
import pytesseract
from pytesseract import Output
import re
import logging
from . import channels
import numpy as np

logger = logging.getLogger(__name__)

def replace_words(text, channel_id):
    channel_info = channels.channels_to_listen.get(channel_id, {})
    replacements = channel_info.get('replacements', {})
    
    for key, value in replacements.items():
        text = text.replace(key, value)
        
    logger.info(f"[replace_words]  modified_text = {text}")
    
    moderation_if_image = channel_info.get('moderation_if_image', False)
    auto_moderation_and_send_text_message = channel_info.get('auto_moderation_and_send_text_message', False)
    
    logger.info(f"[replace_words]  moderation_if_image = {moderation_if_image}")
    logger.info(f"[replace_words]  auto_moderation_and_send_text_message = {auto_moderation_and_send_text_message}")
    
    return text, moderation_if_image, auto_moderation_and_send_text_message

def extract_original_id(chat_id):
    # Преобразовываем chat_id в строку для удобства обработки
    chat_id_str = str(chat_id)
    # Проверяем, начинается ли строка с '-100' и извлекаем число
    match = re.match(r'-100(\d+)', chat_id_str)
    if match:
        return int(match.group(1))  # Возвращаем ID без префикса, преобразованное в int
    return abs(chat_id)  # Возвращаем оригинальный chat_id, если префикс отсутствует
 
def get_average_color(img, x, y, w, h):
    """
    Возвращает средний цвет для области изображения (определяет цвет фона или текста).
    """
    region = img[y:y + h, x:x + w]
    average_color = region.mean(axis=0).mean(axis=0)  # Средний цвет по каналам BGR
    return tuple(map(int, average_color))  # Преобразуем кортеж в int
 
def get_pixel_color(image, x, y):
    """
    Возвращает цвет пикселя по заданным координатам (x, y).
    
    :param image: Изображение, загруженное через OpenCV (cv2.imread)
    :param x: Координата по оси X
    :param y: Координата по оси Y
    :return: Цвет пикселя в формате (B, G, R)
    """
    # Проверка, что координаты находятся в пределах изображения
    if y >= image.shape[0] or x >= image.shape[1]:
        raise ValueError("Координаты выходят за пределы изображения")
    
    # Получение цвета пикселя (BGR)
    pixel_color = image[y, x]  # OpenCV использует порядок BGR
    return tuple(int(c) for c in pixel_color)  # Преобразуем в кортеж целых чисел
 
def replace_words_in_images(file_paths, replacements_dict):
    """
    Функция для поиска и замены слов на изображениях.
    :param file_paths: Список путей к изображениям для обработки
    :param replacements_dict: Словарь, где ключи — это слова для поиска, а значения — слова для замены
    :return: Список путей к обработанным изображениям (тот же список, что и на входе)
    """
    processed_paths = []
def replace_words_in_images(file_paths, replacements_dict):
    """
    Функция для поиска и замены слов на изображениях с использованием Tesseract OCR.
    :param file_paths: Список путей к изображениям для обработки
    :param replacements_dict: Словарь, где ключи — это слова для поиска, а значения — слова для замены
    :return: Список путей к обработанным изображениям (тот же список, что и на входе)
    """
    processed_paths = []

    for image_path in file_paths:
        # Загрузка изображения
        img = cv2.imread(image_path)
        
        # Выполнение OCR и получение данных с изображений
        d = pytesseract.image_to_data(img, output_type=Output.DICT)
        
        # Обработка распознанных слов
        n_boxes = len(d['text'])
        for i in range(n_boxes):
            word = d['text'][i].strip().lower()  # Убираем лишние пробелы и приводим к нижнему регистру
            if word:
                logger.info(f"[replace_words_in_images] Распознано слово: {word}")

            # Проверяем наличие слова в словаре замены
            if word in replacements_dict:
                logger.info(f"[replace_words_in_images] Подлежит замене: {word}")
                (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])

                # Определение цвета фона (можно использовать фиксированный цвет, если фон белый)
                background_color = (255, 255, 255)  # Белый фон

                # Определение цвета текста (например, черный)
                text_color = (0, 0, 0)  # Черный текст

                # Рисуем прямоугольник на месте слова с цветом фона
                cv2.rectangle(img, (x, y), (x + w, y + h), background_color, -1)

                # Наносим новое слово поверх прямоугольника с цветом оригинального текста
                replacement_word = replacements_dict[word]
                
                # Выбор размера шрифта в зависимости от высоты исходного текста
                font_scale = h / 30  # Регулируйте масштаб в зависимости от высоты текста
                cv2.putText(img, replacement_word, (x, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2, cv2.LINE_AA)
    
                logger.info(f"[replace_words_in_images] Заменено на: {replacement_word}")

        # Сохранение измененного изображения по тому же пути
        cv2.imwrite(image_path, img)
        processed_paths.append(image_path)

    return processed_paths
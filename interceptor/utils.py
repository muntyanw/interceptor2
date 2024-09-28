
import cv2
import pytesseract
from pytesseract import Output
import re
import logging
from . import channels
import numpy as np
import os
from telethon import Button

logger = logging.getLogger(__name__)

def is_image_file(file_path):
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in image_extensions

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
    Функция для поиска и замены слов на изображениях с использованием Tesseract OCR.
    :param file_paths: Список путей к изображениям для обработки
    :param replacements_dict: Словарь, где ключи — это слова для поиска, а значения — слова для замены
    :return: Список путей к обработанным изображениям (тот же список, что и на входе)
    """
    processed_paths = []

    for image_path in file_paths:
        
        if not is_image_file(image_path):
           logger.info(f"[replace_words_in_images] Файл {image_path} не является изображением")
           processed_paths.append(image_path)
           continue  # Переходим к следующему файлу
        
        # Загрузка изображения
        img = cv2.imread(image_path)
        
        # Выполнение OCR и получение данных с изображений
        d = pytesseract.image_to_data(img, output_type=Output.DICT)
        
        # Обработка распознанных слов
        n_boxes = len(d['text'])
        for i in range(n_boxes):
            word = d['text'][i].strip().lower()  # Убираем лишние пробелы и приводим к нижнему регистру
            logger.info(f"[replace_words_in_images] word: {word}")
            if word:
                logger.info(f"[replace_words_in_images] Распознано слово: {word}")
                # Проверяем наличие слова в словаре замены
                isRepl = False
                replKey = ""
                for replKey in replacements_dict:
                    logger.info(f"[replace_words_in_images] replKey: {replKey}")
                    ind = word.find(replKey)
                    logger.info(f"[replace_words_in_images] ind: {ind}")
                    if ind > -1:
                        isRepl = True
                        logger.info(f"[replace_words_in_images] isRepl: {isRepl}")
                        break
                
                if isRepl:
                    logger.info(f"[replace_words_in_images] Подлежит замене: {word}")
                    (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])

                    # Определение цвета фона (можно использовать фиксированный цвет, если фон белый)
                    background_color = (255, 255, 255)  # Белый фон

                    # Определение цвета текста (например, черный)
                    text_color = (0, 0, 0)  # Черный текст

                    # Рисуем прямоугольник на месте слова с цветом фона
                    cv2.rectangle(img, (x, y), (x + w, y + h), background_color, -1)

                    # Наносим новое слово поверх прямоугольника с цветом оригинального текста
                    replacement_word = replacements_dict[replKey]
                    
                    # Выбор размера шрифта в зависимости от высоты исходного текста
                    font_scale = h / 30  # Регулируйте масштаб в зависимости от высоты текста
                    cv2.putText(img, replacement_word, (x, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2, cv2.LINE_AA)
        
                    logger.info(f"[replace_words_in_images] Заменено на: {replacement_word}")

        # Сохранение измененного изображения по тому же пути
        cv2.imwrite(image_path, img)
        processed_paths.append(image_path)

    return processed_paths

def find_and_replace_in_images(image_paths, template_image_path, replacement_image_path):
    """
    Функция для поиска шаблона в каждом изображении из списка и замены его на новое изображение.
    :param image_paths: Список путей к изображениям
    :param template_image_path: Путь к изображению-шаблону (образцу для поиска)
    :param replacement_image_path: Путь к изображению для замены найденного участка
    :return: Список путей к обработанным изображениям (перезаписанные исходные изображения)
    """
    # Загрузка шаблона и изображения для замены
    template_img = cv2.imread(template_image_path, 0)  # Шаблон (образец)
    replacement_img = cv2.imread(replacement_image_path)  # Изображение для замены
    
    # Инициализация ORB детектора
    orb = cv2.ORB_create()

    processed_paths = []

    # Цикл по каждому изображению из списка
    for image_path in image_paths:
        # Загрузка текущего изображения
        main_img = cv2.imread(image_path)

        # Нахождение ключевых точек и дескрипторов для шаблона и текущего изображения
        kp1, des1 = orb.detectAndCompute(template_img, None)
        kp2, des2 = orb.detectAndCompute(cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY), None)

        # Используем BFMatcher для сопоставления
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        # Сортировка по расстоянию
        matches = sorted(matches, key=lambda x: x.distance)

        # Получение точек на изображениях
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 2)

        # Вычисление гомографии для преобразования изображения
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        # Размеры шаблона (образа)
        h, w = template_img.shape

        # Получение координат углов шаблона на изображении
        pts = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)

        # Определение области, куда нужно вставить новое изображение
        (x_min, y_min) = np.int32(dst.min(axis=0).ravel())
        (x_max, y_max) = np.int32(dst.max(axis=0).ravel())

        # Изменение размера изображения для замены в соответствии с найденной областью
        replacement_resized = cv2.resize(replacement_img, (x_max - x_min, y_max - y_min))

        # Замена найденной области на новое изображение
        main_img[y_min:y_max, x_min:x_max] = replacement_resized

        # Сохранение измененного изображения по тому же пути
        cv2.imwrite(image_path, main_img)

        # Добавление пути к обработанному изображению в список
        processed_paths.append(image_path)

    return processed_paths

def update_buttons(buttons, replacements):
    """
    Метод для обновления ссылок на кнопках в соответствии с текстом кнопки.

    :param buttons: Список строк с инлайн-кнопками (список списков кнопок).
    :param replacements: Словарь с соответствием текстов кнопок и новых ссылок, например:
                         {'Текущая кнопка': 'https://новая-ссылка.com'}
    :return: Обновленный список строк с кнопками.
    """
    updated_buttons = []

    # Проходим по строкам кнопок
    if buttons is not None:
        for row in buttons:
            updated_row = []
            
            # Проходим по каждой кнопке в строке (в строке находится список кнопок)
            for button in row:
                if hasattr(button, 'url'):
                    # Если текст кнопки есть в replacements, заменяем ссылку
                    if button.text in replacements:
                        new_url = replacements[button.text]
                        updated_row.append(Button.url(button.text, new_url))
                    else:
                        # Если текст кнопки не найден в replacements, оставляем кнопку без изменений
                        updated_row.append(button)
                else:
                    # Если кнопка не является URL-кнопкой, добавляем её без изменений
                    updated_row.append(button)
            
            # Добавляем обновленную строку кнопок в результирующий список
            updated_buttons.append(updated_row)

    return updated_buttons

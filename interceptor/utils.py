import cv2
import pytesseract
from pytesseract import Output
import re
import logging
from . import channels
import numpy as np
import os
from telethon import Button
import hashlib
from telethon.tl.custom import Button
from telethon.tl.custom.messagebutton import MessageButton
import pprint
from moviepy.editor import VideoFileClip
from collections.abc import Iterable
from pydub import AudioSegment
import ffmpeg

# Инициализация pprint
pp = pprint.PrettyPrinter(indent=2)

logger = logging.getLogger(__name__)

def logOneAttribut(attribute):
    if hasattr(attribute, '__dict__'):
        logger.info(f"[log_attributes] Содержимое атрибута {attribute.__class__.__name__}: {pp.pformat(attribute.__dict__)}")
    else:
        # Если __dict__ нет, просто выводим объект
        logger.info(f"[log_attributes] Неизвестный атрибут: {attribute}")

# Функция для логирования атрибутов
def log_attributes(attributes):
    if attributes:
        logger.info(f"[log_attributes] attributes не пустий.")
        if isinstance(attributes, Iterable):
            for attribute_list in attributes:
                if attribute_list and isinstance(attribute_list, Iterable):
                    for attribute in attribute_list:
                        logOneAttribut(attribute)
                else:
                    if attribute_list:
                        logger.info(f"[log_attributes] attribute_list not iterable.")
                        logOneAttribut(attribute_list)
                    else:
                        logger.info(f"[log_attributes] attribute_list empty.")
        else:
            logOneAttribut(attributes)
    else:
        logger.info(f"[log_attributes] Нет атрибутов.")

def is_image_file(file_path):
    # Добавляем проверку на None
    if file_path is None:
        logger.error("[is_image_file] Путь к файлу не должен быть None.")
        return False

    ext = os.path.splitext(file_path)[1].lower()
    return ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']

def is_sticker(file_path):
    # Добавляем проверку на None
    if file_path is None:
        logger.error("[is_image_file] Путь к файлу не должен быть None.")
        return False

    ext = os.path.splitext(file_path)[1].lower()
    return ext in ['.webp']

def replace_words(text, channel_id):
    logger.info(f"[replace_words]  text = {text}")
    channel_info = channels.channels_to_listen.get(channel_id, {})
    replacements = channel_info.get('replacements', {})

    text = replace_links(text, channels.replacement_urls)
        
    for key, value in replacements.items():
        text = text.replace(key, value)
        
    logger.info(f"[replace_words]  modified_text = {text}")
    
    moderation_if_image = channel_info.get('moderation_if_image', False)
    auto_moderation_and_send_text_message = channel_info.get('auto_moderation_and_send_text_message', False)
    channels_to_send = channel_info.get('channels_to_send', False)
    
    return text, moderation_if_image, auto_moderation_and_send_text_message, channels_to_send

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

def formatted_buttons(buttons):
    # Преобразуем кнопки в нужный формат
    formatted_buttons = []
    for row in buttons:
        button_row = []
        for btn in row:
            # Логируем тип кнопки перед обработкой
            logger.info(f"[formatted_buttons] Обрабатываем кнопку: {btn}")
            
            # Проверяем, если это объект MessageButton
            if isinstance(btn, MessageButton):
                # Для URL-кнопок
                if btn.url:
                    button_row.append(Button.url(btn.text, btn.url))
                    logger.info(f"[formatted_buttons] Преобразована URL-кнопка: текст={btn.text}, url={btn.url}")
                # Для инлайн-кнопок с callback
                elif btn.data:
                    button_row.append(Button.inline(btn.text, btn.data))
                    logger.info(f"[formatted_buttons] Преобразована инлайн-кнопка: текст={btn.text}, data={btn.data}")
                else:
                    logger.warning(f"[formatted_buttons] Неизвестный тип кнопки: {btn}")
            else:
                logger.warning(f"[formatted_buttons] Неизвестный тип кнопки: {type(btn).__name__}")

        if button_row:
            logger.info(f"[formatted_buttons] Добавлена строка кнопок: {button_row}")
            formatted_buttons.append(button_row)

    # Логируем результат преобразования кнопок
    logger.info(f"[formatted_buttons] Все кнопки преобразованы")
    return formatted_buttons

def get_file_extension(file_path):
    """
    Возвращает расширение файла.

    :param file_path: Путь к файлу.
    :return: Расширение файла (например, '.txt', '.jpg'). Если расширения нет, возвращает пустую строку.
    """
    return os.path.splitext(file_path)[1].lower()

def has_file_with_extension(file_list, extension):
    """
    Проверяет, есть ли в списке файлов хотя бы один файл с указанным расширением.

    :param file_list: Список путей к файлам.
    :param extension: Расширение для проверки (например, '.ogg').
    :return: True, если найден файл с указанным расширением, иначе False.
    """
    extension = extension.lower()  # Приводим расширение к нижнему регистру для надежности
    for file_path in file_list:
        if os.path.splitext(file_path)[1].lower() == extension:
            return True
    return False

def has_file_with_extensions(file_list, extensions):
    """
    Проверяет, есть ли в списке файлов хотя бы один файл с указанным списком расширений.

    :param file_list: Список путей к файлам.
    :param extensions: Список расширений для проверки (например, ['.ogg', '.oga']).
    :return: True, если найден файл с любым из указанных расширений, иначе False.
    """
    extensions = [ext.lower() for ext in extensions]  # Приводим все расширения к нижнему регистру для надежности
    for file_path in file_list:
        if os.path.splitext(file_path)[1].lower() in extensions:
            return True
    return False

def update_buttons(buttons, replacements):
    """
    Метод для обновления ссылок на кнопках в соответствии с текстом кнопки.

    :param buttons: Список строк с инлайн-кнопками (список списков кнопок).
    :param replacements: Словарь с соответствием текстов кнопок и новых ссылок, например:
                         {'Текущая кнопка': 'https://новая-ссылка.com' или 'callback_data': 'new_callback_data'}
    :return: Обновленный список строк с кнопками.
    """
    updated_buttons = []

    if buttons is not None:
        logger.info(f"[update_buttons] Начинаем обновление кнопок. buttons = {buttons}")
        for row in buttons:
            updated_row = []
            logger.info(f"[update_buttons] Обрабатываем строку кнопок: {row}")

            for button in row:
                logger.info(f"[update_buttons] Обрабатываем кнопку: {button}")

                if hasattr(button, 'url'):
                    logger.info(f"[update_buttons] Кнопка {button.text} является URL-кнопкой.")
                    if button.text in replacements:
                        new_url = replacements[button.text]
                        logger.info(f"[update_buttons] Заменяем URL для кнопки '{button.text}' на '{new_url}'.")
                        updated_row.append(Button.url(button.text, new_url))
                    else:
                        logger.info(f"[update_buttons] Текст кнопки '{button.text}' не найден в replacements. Оставляем без изменений.")
                        updated_row.append(button)
                elif hasattr(button, 'data'):
                    logger.info(f"[update_buttons] Кнопка {button.text} является инлайн-кнопкой.")
                    if button.text in replacements:
                        new_data = replacements[button.text]
                        logger.info(f"[update_buttons] Заменяем данные для кнопки '{button.text}' на '{new_data}'.")
                        updated_row.append(Button.inline(button.text, new_data))
                    else:
                        logger.info(f"[update_buttons] Текст кнопки '{button.text}' не найден в replacements. Оставляем без изменений.")
                        updated_row.append(button)
                else:
                    logger.info(f"[update_buttons] Тип кнопки не поддерживается. Оставляем кнопку '{button.text}' без изменений.")
                    updated_row.append(button)

            logger.info(f"[update_buttons] Добавляем обновлённую строку кнопок: {updated_row}")
            updated_buttons.append(updated_row)
        logger.info("[update_buttons] Обновление кнопок завершено.")
    else:
       logger.info(f"[update_buttons] Нет кнопок.") 
    
    return updated_buttons

def hash_file(file_path):
    """Вычисляет хэш для файла по его содержимому."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

async def get_bot_info(client):
    # Fetch the bot's info
    me = await client.get_me()
    print(f"Bot's Name: {me.username}")
    
def check_file(file_path):
    # Проверяем, существует ли файл
    if os.path.isfile(file_path):
        # Проверяем, не пустой ли файл
        if os.path.getsize(file_path) > 0:
            print(f"Файл '{file_path}' существует и не пустой.")
            return True
        else:
            print(f"Файл '{file_path}' существует, но он пустой.")
            return False
    else:
        print(f"Файл '{file_path}' не существует.")
        return False
    
def remove_file(file_path):
    try:
        # Проверяем, существует ли файл
        if os.path.isfile(file_path):
            # Удаляем файл
            os.remove(file_path)
            logger.info(f"Файл '{file_path}' успешно удалён.")
        else:
            logger.info(f"Файл '{file_path}' не существует.")
    except Exception as e:
        logger.info(f"Ошибка при удалении файла: {e}")

# Получение пути к файлу сессии
def get_session_web_file_path(request, settings):
    session_key = request.session.session_key
    if not session_key:
        logger.error("[get_session_file_path] Не удалось получить session_key.")
        return None

    session_file_path = os.path.join(settings.SESSION_FILE_PATH, session_key)
    logger.info(f"[get_session_file_path] Путь к файлу сессии веб: {session_file_path}")
    return session_file_path

def removeFilesSessions(settings):
    paths = [
        settings.BASE_DIR + '/' + channels.name_session_client + ".session",
        settings.BASE_DIR + '/' + channels.name_session_client + ".session-journal",
        settings.BASE_DIR + '/' + channels.name_session_bot + ".session",
        settings.BASE_DIR + '/' + channels.name_session_bot + ".session-journal"
    ]
    
    for path in paths:
        logger.info(f"[removeFilesSessions] remove: {path}")
        remove_file(path)

    logger.info("[removeFilesSessions] Клиентская сессия удалена.")

import re
import logging

logger = logging.getLogger(__name__)

def replace_links(text, replacement_urls):
    """
    Заменяет ссылки в тексте в соответствии с заданными правилами.
    
    :param text: Исходный текст, в котором ищем и заменяем ссылки.
    :param replacement_urls: Словарь, где ключи - это строки, которые ищем в ссылках,
                              а значения - текст, на который заменяем ссылки.
    :return: Измененный текст.
    """

    logger.info(f"[replace_links] ищем ссылки с указанным текстом")
    # Регулярное выражение для поиска ссылок, исключая *, ), и пробелы на границе
    link_pattern = re.compile(r'https?://[^\s\*\)]+')
    
    # Функция для замены ссылок в зависимости от соответствий
    def replace_match(match):
        link = match.group(0)
        if link:
            logger.info(f"[replace_links] найдены линки {link}")
        for search_text, replace_text in replacement_urls.items():
            if search_text in link:
                logger.info(f"[replace_links] найден текст {search_text} вся ссылка меняется на {replace_text}")
                return replace_text
        logger.info(f"[replace_links] линк не меняется")
        return link  # Если совпадений нет, оставляем ссылку без изменений

    # Заменяем ссылки в тексте
    result = link_pattern.sub(replace_match, text)
    logger.info(f"[replace_links] Результирующий текст {result}")
    return result


def convert_round_video(input_file, output_file):
    """
    Конвертирует круговое видео из .oga в .mp4.
    
    :param input_file: Путь к входному .oga файлу (круговое видео).
    :param output_file: Путь для сохранения выходного .mp4 файла.
    """
    try:
        logger.info(f"[convert_round_video] Попытка конвертации {output_file}")
        # Загрузка видеофайла
        video_clip = VideoFileClip(input_file)
        
        # Конвертация и сохранение в формате MP4
        video_clip.write_videofile(output_file, codec='libx264')

        logger.info(f"[convert_round_video] Файл успешно конвертирован и сохранен как {output_file}")
    except Exception as e:
        logger.info(f"[convert_round_video] Ошибка при конвертации: {e}")

def convert_oga_to_mp3(input_file, output_file):
    """
    Конвертирует аудиофайл из .oga в .mp3.

    :param input_file: Путь к входному .oga файлу.
    :param output_file: Путь для сохранения выходного .mp3 файла.
    """
    try:
        logger.info(f"[convert_oga_to_mp3] Загрузка .oga файла {input_file}")
        
        # Использование ffmpeg для конвертации
        ffmpeg.input(input_file).output(output_file, format='mp3').run(overwrite_output=True)
        
        logger.info(f"[convert_oga_to_mp3] Файл успешно конвертирован и сохранен как {output_file}")
        
    except Exception as e:
        logger.info(f"[convert_oga_to_mp3] Ошибка при конвертации: {e}")

def change_file_extension(file_path, new_extension):
    """
    Заменяет расширение файла на заданное.
    
    :param file_path: Путь к файлу, у которого нужно заменить расширение.
    :param new_extension: Новое расширение файла (например, 'mp4').
    :return: Путь к файлу с новым расширением.
    """
    # Убираем точку из нового расширения, если она есть
    new_extension = new_extension.lstrip('.')
    
    # Изменяем расширение файла
    new_file_path = os.path.splitext(file_path)[0] + f'.{new_extension}'
    
    return new_file_path

def get_video_dimensions(file_path):
    """
    Получает размеры видео с помощью MoviePy.
    :param file_path: Путь к видеофайлу.
    :return: (ширина, высота, длительность)
    """
    video = VideoFileClip(file_path)
    return video.w, video.h, int(video.duration)

def get_video_dimensions_cv2(file_path):
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return None, None, None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps else None
    cap.release()
    return width, height, duration, fps

def is_video_file(file_path):
    """
    Определяет, является ли файл видео по его расширению.
    
    :param file_path: Путь к файлу.
    :return: True, если файл является видео, иначе False.
    """
    # Список расширений видеофайлов
    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
    
    # Получаем расширение файла
    file_extension = file_path.lower().split('.')[-1]
    
    # Проверяем, есть ли расширение в списке видео
    return f".{file_extension}" in video_extensions

def add_closing_bracket_if_needed(text):
    if text is not None and text.count('(') > text.count(')'):
        text += ')'
    return text

import ffmpeg

def generate_thumbnail(video_path, time='00:00:01'):
    # Получаем базовое имя файла без расширения
    base_name = os.path.splitext(video_path)[0]
    # Формируем имя миниатюры с расширением .jpg
    thumbnail_path = f"{base_name}.jpg"
    try:
        (
            ffmpeg
            .input(video_path, ss=time)
            .filter('scale', 320, -1)
            .output(thumbnail_path, vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        print('Ошибка при создании миниатюры:', e)
        raise
    # Возвращаем путь к миниатюре
    return thumbnail_path





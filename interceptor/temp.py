      data = json.loads(text_data)
        message_text = data.get("new_text", "")
        new_files = data.get("new_files", [])
        existing_files = data.get("existing_files", [])

        file_objects = []

        # Обработка новых файлов
        for file in new_files:
            file_name = file.get("name")
            file_data = file.get("data").split(",")[1]  # Убираем префикс 'data:image/jpeg;base64,'
            file_bytes = base64.b64decode(file_data)
            file_obj = BytesIO(file_bytes)

            # Вычисляем md5 хэш-сумму
            md5_checksum = hashlib.md5(file_bytes).hexdigest()

            # Создаем объект InputFile
            input_file = InputFile(file_obj, file_name, len(file_bytes), md5_checksum)
            file_objects.append(input_file)

        # Обработка существующих файлов
        for file_url in existing_files:
            # Здесь используем подход с повторным созданием InputFile
            with open(file_url, 'rb') as f:
                file_bytes = f.read()
                file_obj = BytesIO(file_bytes)
                
                # Вычисляем md5 хэш-сумму
                md5_checksum = hashlib.md5(file_bytes).hexdigest()

                input_file = InputFile(file_obj, file_url.split('/')[-1], len(file_bytes), md5_checksum)
                file_objects.append(input_file)

        await send_message_to_channels(message_text, file_objects)

        # Удаляем временные файлы после отправки
        for file in new_files:
            file_name = file.get("name")
            file_path = os.path.join("/tmp", file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
        logger.info(f"[TelegramConsumer] Получены данные через WebSocket: {text_data}")
        data = json.loads(text_data)
        message_text = data.get("new_text", "")
        new_files = data.get("new_files", [])
        existing_files = data.get("existing_files", [])

        logger.info(f"[TelegramConsumer] Получены новые файлы через WebSocket: {new_files}")
        logger.info(
            f"[TelegramConsumer] Получены существующие файлы через WebSocket: {existing_files}"
        )

        file_objects = []

        # Обработка новых файлов и их сохранение на диск
        for file in new_files:
            file_name = file.get("name")
            file_data = file.get("data").split(",")[
                1
            ]  # Убираем префикс 'data:image/jpeg;base64,'
            file_bytes = base64.b64decode(file_data)

            # Сохраняем файл на диск
            file_path = os.path.join("/tmp", file_name)
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            # Используем путь к файлу для InputFile
            input_file = InputFile(file_path)
            file_objects.append(input_file)

        # Обработка существующих файлов
        for file_url in existing_files:
            input_file = InputFile(file_url)
            file_objects.append(input_file)

        await send_message_to_channels(message_text, file_objects)

        # Удаляем временные файлы после отправки
        for file in new_files:
            file_name = file.get("name")
            file_path = os.path.join("/tmp", file_name)
            if os.path.exists(file_path):
                os.remove(file_path)

        logger.info(
            f"[TelegramConsumer] Сообщение отправлено через Telethon: {message_text}"
        )
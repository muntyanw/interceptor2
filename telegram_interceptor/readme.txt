Запуск приложения:

1. зайти в директорию 
cd /usr/share/nginx/html/interceptor
2. запустить среду питона
source venv/bin/activate

1 и 2 делается один раз при открытии терминала

3. запустить сам скрипт
uvicorn telegram_interceptor.asgi:application --host 0.0.0.0 --port 8000 --reload

Настройки:

1. Каналы - файл \interceptor\channels.py
для каждого канала который слушаем есть такая структура 

channels_to_listen = {
	4593819858 #айди канала смотреть на специальной страницестранице#: {
			'moderation_if_image': True, #если в сообщении есть картинка то оно отсылается на модерацию#
			
			'replacements': {
				'слово1': 'замена1', #что на что меняем#
				'слово2': 'замена2',
				'слово3': 'замена3',
				'слово4': 'замена4',
			}
		},
......
}

2. Каналы в которые отсылаем 
channels_to_send = ['@имя канала, контакта', '@secondcontact']

Клонирование приложения

cp -r /usr/share/nginx/html/interceptor /usr/share/nginx/html/interceptor2

sudo nano /etc/nginx/sites-available/interceptor2

в файл записать
************************************************************
server {
    listen 8001;  # Новый порт для второго экземпляра
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8002;  # Внутренний порт, который будет использовать Uvicorn
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /usr/share/nginx/html/interceptor2/static/;
    }

    location /media/ {
        alias /usr/share/nginx/html/interceptor2/media/;
    }
}
*******************************************************************

sudo ln -s /etc/nginx/sites-available/interceptor2 /etc/nginx/sites-enabled/

тут в коде изменить порт
 // Подключение к WebSocket для приема сообщений в реальном времени
        const chatSocket = new WebSocket(
          "ws://" + window.location.host + ":8000/ws/telegram/"
        );

Запуск второго приложения

cd /usr/share/nginx/html/interceptor2
source venv/bin/activate
uvicorn telegram_interceptor.asgi:application --host 127.0.0.1 --port 8002 --reload

uvicorn telegram_interceptor.asgi:application --host 127.0.0.1 --port 8000




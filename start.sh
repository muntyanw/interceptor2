#!/bin/bash
cd /usr/share/nginx/html/interceptor
source venv/bin/activate
export PORT=8080
uvicorn telegram_interceptor.asgi:application --host 0.0.0.0 --port $PORT
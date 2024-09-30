#!/bin/bash
cd /interceptor
source venv/bin/activate
export PORT=8000
uvicorn telegram_interceptor.asgi:application --host 0.0.0.0 --port $PORT
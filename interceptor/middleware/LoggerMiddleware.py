from ..logger import logger  # Убедитесь, что используете правильный путь импорта

class LoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Код, выполняемый перед обработкой представлением
        logger.info(f"Request path: {request.path}")

        response = self.get_response(request)

        # Код, выполняемый после обработки представлением
        logger.info(f"Response status code: {response.status_code}")

        return response

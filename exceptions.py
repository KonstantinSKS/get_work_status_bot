class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""

    pass


class ApiAnswerError(Exception):
    """Ошибка при запросе к API."""

    pass


class MainError(Exception):
    """Ошибка при обработке функций в основной логике бота."""

    pass

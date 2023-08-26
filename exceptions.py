class TelegramSendMessageError(Exception):
    """Ошибка при отправке сообщения в Telegram."""
    pass


class HTTPStatusNotOk(Exception):
    """Статус запроса к API отличный от "Ok"."""
    pass

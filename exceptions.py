class ConnectionError(Exception):
    """Ошибка соединения с сервисом API."""

    pass


class DecodeError(Exception):
    """Ошибка декодирования JSON."""

    pass

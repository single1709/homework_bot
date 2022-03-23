class NoMessageError(Exception):
    """Отправка исключений в лог."""

    pass


class WithMessageError(Exception):
    """Отправка исключений в лог и в чат."""

    pass

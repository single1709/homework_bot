class NoMessageError(Exception):
    """Отправка исключений в лог.

    уровень Error.
    """

    pass


class NoMessageDebug(Exception):
    """Отправка исключений в лог.

    уровень Debug.
    """
    pass

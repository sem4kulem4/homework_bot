class APIHomeworkError(Exception):
    """Исключение, если API по какой-либо причине не выдал список ДЗ."""

    pass


class EmptyDictError(Exception):
    """Исключение, если в ответе API список ДЗ оказалася пустым."""

    pass


class APINotAvailableError(Exception):
    """Исключение, когда код ответа API отличен от 200"""

    pass


class TokensUnavailableError(Exception):
    """Исключение, когда код отсутствует один из токенов для бота"""

    pass

class ApiRequestError(Exception):
    """Ошибки при запросе к апи."""

    pass


class HomeworkKeyError(Exception):
    """Ошибки при отсутствии ключей в домашке."""

    pass


class JsonConvertError(Exception):
    """Ошибки при преобразовании в JSON."""

    pass

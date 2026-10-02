"""Общие обёртки операций и кэш на основе замыкания."""

import time
from contextvars import ContextVar
from functools import wraps

DB_ERROR = object()
CANCELLED = object()
_ERROR_DEPTH = ContextVar("db_error_depth", default=0)


def handle_db_errors(func):
    """Печатает ошибку один раз, на внешней границе вложенных вызовов."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        depth = _ERROR_DEPTH.get()
        token = _ERROR_DEPTH.set(depth + 1)
        try:
            return func(*args, **kwargs)
        except Exception as error:
            # Внутренний вызов прерывает операцию целиком, а не возвращает
            # ошибку вместо ожидаемых данных в середину вычислений.
            if depth:
                raise
            if isinstance(error, FileNotFoundError):
                print(
                    "Ошибка: Файл данных не найден. Возможно, БД не инициализирована."
                )
            elif isinstance(error, KeyError):
                print(f"Ошибка: Таблица или столбец {error} не найден.")
            elif isinstance(error, ValueError):
                print(f"Ошибка валидации: {error}")
            elif isinstance(error, OSError):
                print(f"Ошибка работы с файлом: {error}")
            else:
                print(f"Произошла непредвиденная ошибка: {error}")
            return DB_ERROR
        finally:
            _ERROR_DEPTH.reset(token)

    return wrapper


def confirm_action(action_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            answer = input(f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ')
            if answer != "y":
                print("Операция отменена.")
                return CANCELLED
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        started = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started
            print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд")

    return wrapper


def create_cacher():
    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            value = value_func()
            # Не сохраняем ошибки и ограничиваем рост памяти долгого сеанса.
            if value is DB_ERROR or value is CANCELLED:
                return value
            if len(cache) >= 256:
                cache.clear()
            cache[key] = value
        return cache[key]

    cache_result.clear = cache.clear
    return cache_result

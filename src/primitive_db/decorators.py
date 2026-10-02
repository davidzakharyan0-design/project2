"""Общие обёртки операций и кэш на основе замыкания."""

import time

from primitive_db.constants import (
    CACHE_LIMIT,
    CANCELLED,
    CONFIRMATION_ANSWER,
    DB_ERROR,
)

# Приложение однопоточное: счётчик нужен только для вложенных вызовов.
_error_depth = 0


def preserve_metadata(func):
    """Сохраняет сведения о функции без дополнительных библиотек."""

    def decorate(wrapper):
        """Копирует имя, документацию и ссылку на исходную функцию."""
        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper.__annotations__ = dict(func.__annotations__)
        wrapper.__wrapped__ = func
        return wrapper

    return decorate


def handle_db_errors(func):
    """Печатает ошибку один раз, на внешней границе вложенных вызовов."""

    @preserve_metadata(func)
    def wrapper(*args, **kwargs):
        """Вызывает исходную функцию с поведением данного декоратора."""
        global _error_depth
        depth = _error_depth
        _error_depth += 1
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
            _error_depth = depth

    return wrapper


def confirm_action(action_name):
    """Создаёт декоратор подтверждения указанного действия."""

    def decorator(func):
        """Оборачивает функцию запросом подтверждения."""

        @preserve_metadata(func)
        def wrapper(*args, **kwargs):
            """Вызывает исходную функцию с поведением данного декоратора."""
            answer = input(f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ')
            if answer != CONFIRMATION_ANSWER:
                print("Операция отменена.")
                return CANCELLED
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func):
    """Добавляет измерение времени выполнения функции."""

    @preserve_metadata(func)
    def wrapper(*args, **kwargs):
        """Вызывает исходную функцию с поведением данного декоратора."""
        started = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started
            print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд")

    return wrapper


def create_cacher():
    """Возвращает функцию с независимым словарём кэша в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        """Возвращает сохранённое значение либо вычисляет и кэширует его."""
        if key not in cache:
            value = value_func()
            # Не сохраняем ошибки и ограничиваем рост памяти долгого сеанса.
            if value is DB_ERROR or value is CANCELLED:
                return value
            if len(cache) >= CACHE_LIMIT:
                cache.clear()
            cache[key] = value
        return cache[key]

    cache_result.clear = cache.clear
    return cache_result

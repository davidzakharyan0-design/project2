"""Проверки обёрток, кэша и их взаимодействия с файлами."""

import os

from primitive_db import core, decorators, engine
from primitive_db.constants import CANCELLED, DB_ERROR, META_FILE
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_metadata, load_table_data


def command(text):
    """Выполняет команду в текущей тестовой директории."""
    return engine.process_command(load_metadata(META_FILE), text)


def create_demo():
    """Создаёт одну запись для проверки отмены и изменения данных."""
    command("create_table demo name:str age:int")
    command('insert into demo values ("Ann", 28)')


def test_nested_error_stops_operation():
    """Ошибка выводится один раз и прерывает всю цепочку вызовов."""
    errors = [KeyError("x"), ValueError("bad"), FileNotFoundError(), OSError("disk")]
    for error in errors:
        messages = []
        continued = []

        @handle_db_errors
        def inner():
            """Возбуждает проверяемое исключение."""
            raise error

        @handle_db_errors
        def outer():
            """Проверяет прекращение работы после внутреннего исключения."""
            inner()
            continued.append(True)

        decorators.print = messages.append
        try:
            assert outer() is DB_ERROR
            assert len(messages) == 1
            assert not continued
        finally:
            del decorators.print
    assert core.validate_name("../bad") is DB_ERROR
    assert core.validate_name("good") is None  # Счётчик вложенности восстановлен.


def test_confirmation_and_metadata():
    """Только y разрешает вызов, сведения об исходной функции сохранены."""
    called = []

    @confirm_action("тест")
    def operation():
        """Документация операции."""
        called.append(True)
        return 42

    assert operation.__name__ == "operation"
    assert operation.__doc__ == "Документация операции."
    assert operation.__wrapped__.__name__ == "operation"
    previous_input = decorators.input
    try:
        for answer in ["n", "", "yes", "Y"]:
            decorators.input = lambda question: answer
            assert operation() is CANCELLED
        assert not called
        decorators.input = lambda question: "y"
        assert operation() == 42
        assert called == [True]
    finally:
        decorators.input = previous_input


def test_timing():
    """Время форматируется с тремя знаками, результат не теряется."""

    @log_time
    def sample(value):
        """Возвращает аргумент без изменений."""
        return value

    messages = []
    ticks = iter([1, 1.125])
    previous_clock = decorators.time.monotonic
    decorators.time.monotonic = lambda: next(ticks)
    decorators.print = messages.append
    try:
        assert sample(12) == 12
        assert messages == ["Функция sample выполнилась за 0.125 секунд"]
    finally:
        decorators.time.monotonic = previous_clock
        del decorators.print


def test_cacher_hits_and_isolation():
    """Повторный ключ не вызывает вычисление, разные кэши независимы."""
    calls = []

    def calculate():
        """Считает количество реальных вычислений."""
        calls.append(True)
        return []

    cacher = create_cacher()
    assert cacher("key", calculate) == []
    assert cacher("key", calculate) == []
    assert len(calls) == 1
    create_cacher()("key", calculate)
    assert len(calls) == 2
    assert cacher("error", lambda: DB_ERROR) is DB_ERROR
    assert cacher("error", lambda: 4) == 4

    def failure():
        """Имитирует ошибку вычисления."""
        raise ValueError("bad")

    try:
        cacher("failed", failure)
    except ValueError:
        pass
    else:
        raise AssertionError("Ошибка вычисления должна распространяться.")
    assert cacher("failed", lambda: 3) == 3


def test_select_cache_protection_and_freshness():
    """Кэш не портится извне и учитывает содержимое таблицы и типы."""
    core._select_cache.clear()
    rows = [{"ID": 1, "age": 28}]
    calls = []
    original_matches = core.matches

    def count_matches(row, condition):
        """Считает число реально выполненных фильтраций."""
        calls.append(True)
        return original_matches(row, condition)

    core.matches = count_matches
    try:
        first = core.select(rows, {"age": 28})
        first[0]["age"] = 99
        assert core.select(rows, {"age": 28})[0]["age"] == 28
        assert len(calls) == 1
        rows[0]["age"] = 29
        assert core.select(rows, {"age": 28}) == []
        assert core.select(rows, {"age": 29}) == rows
        assert core.select(rows, {"age": True}) == []
    finally:
        core.matches = original_matches


def test_cancel_preserves_both_files():
    """Отказ от удаления не меняет файлы и не сообщает об успехе."""
    create_demo()
    before = load_table_data("demo")
    metadata = load_metadata(META_FILE)
    previous_input = decorators.input
    messages = []
    decorators.input = lambda question: "n"
    engine.print = messages.append
    try:
        assert command("delete from demo where ID=1") is CANCELLED
        assert command("drop_table demo") is CANCELLED
        assert not any("успешно" in message for message in messages)
        assert load_table_data("demo") == before
        assert load_metadata(META_FILE) == metadata
    finally:
        decorators.input = previous_input
        del engine.print


def test_cache_after_mutations():
    """Все виды изменений исключают использование устаревшей выборки."""
    create_demo()
    command("select from demo")
    command("update demo set age=29 where ID=1")
    assert core.select(load_table_data("demo"))[0]["age"] == 29
    command('insert into demo values ("Bob", 30)')
    assert len(core.select(load_table_data("demo"))) == 2
    command("delete from demo where ID=1")
    assert core.select(load_table_data("demo"))[0]["name"] == "Bob"
    command("drop_table demo")
    command("create_table demo name:str age:int")
    assert core.select(load_table_data("demo")) == []


def test_two_sessions_and_recovery():
    """Главный цикл переживает ошибку и читает данные в следующем сеансе."""
    create_demo()
    original_prompt = engine.prompt.string
    messages = []
    engine.print = lambda value: messages.append(str(value))
    try:
        commands = iter(["bad_command", "update demo set age=29 where ID=1", "exit"])
        engine.prompt.string = lambda question: next(commands)
        engine.run()
        commands = iter(["select from demo", "exit"])
        engine.run()
        assert any("29" in message and "Ann" in message for message in messages)
        assert os.path.exists("data/demo.json")
    finally:
        engine.prompt.string = original_prompt
        del engine.print

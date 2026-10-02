"""Функциональные проверки таблиц и CRUD без классов и тестовых библиотек."""

import json
import os

from primitive_db.constants import DB_ERROR, META_FILE
from primitive_db.core import create_table, insert
from primitive_db.engine import process_command
from primitive_db.parser import parse_command, parse_set, parse_where
from primitive_db.utils import load_metadata, load_table_data, save_table_data


def command(text):
    """Выполняет команду с актуальными метаданными тестовой базы."""
    return process_command(load_metadata(META_FILE), text)


def create_users():
    """Создаёт таблицу с тремя типами данных."""
    command("create_table users name:str age:int is_active:bool")


def test_crud_and_persistence():
    """Проверяет запись на диск, выборку, изменение и удаление."""
    create_users()
    command('insert into users values ("Sergei", 28, true)')
    assert command("select from users where age=28") is not DB_ERROR
    command('update users set age=29 where name="Sergei"')
    assert load_table_data("users")[0]["age"] == 29
    with open("data/users.json", encoding="utf-8") as file:
        assert json.load(file)[0]["name"] == "Sergei"
    command("delete from users where ID=1")
    assert load_table_data("users") == []
    assert command("info users") is not DB_ERROR


def test_parser_quotes_and_types():
    """Проверяет кавычки, запятые и типы литералов."""
    create_users()
    command('insert into users values ("A, B where = test", -2, false)')
    assert load_table_data("users")[0]["name"] == "A, B where = test"
    assert parse_where('name="28"') == {"name": "28"}
    assert parse_set("age=3, is_active=true") == {"age": 3, "is_active": True}
    assert parse_where("name='O\\'Brien'") == {"name": "O'Brien"}
    assert parse_where('name="a\\n\\"b"') == {"name": 'a\n"b'}
    assert parse_command("update t set where=2 where ID=1")[2] == {"where": 2}
    assert parse_command('insert into t values ("", +2, false)')[2] == ["", 2, False]
    assert parse_where('имя="Анна"') == {"имя": "Анна"}


def test_invalid_commands_preserve_file():
    """Ошибочные команды не меняют существующие записи."""
    create_users()
    command('insert into users values ("Sergei", 28, true)')
    before = load_table_data("users")
    invalid = [
        'insert into users values ("Bad", true, false)',
        'insert into users values ("Bad", "28", false)',
        'insert into users values ("Bad", 2)',
        'insert into users values ("Bad", 2, 1)',
        "update users set ID=2 where ID=1",
        'update users set age="bad" where ID=1',
        "update users set missing=2 where ID=1",
        "select from users where missing=1",
        "delete from users where ID=true",
        "delete from users",
        "insert into users values (Bad, 2, true)",
        'insert into users values ("Bad", 2.5, true)',
        'insert into users values ("unterminated, 2, true)',
        'insert into users values ("Bad", 2, true,)',
        "update users set age=1, where ID=1",
        "unknown_command",
        "create_table users name:str",
        "create_table broken price:float",
        "create_table repeated name:str name:int",
        "create_table ../outside name:str",
    ]
    for text in invalid:
        assert command(text) is DB_ERROR, text
        assert load_table_data("users") == before, text
    assert set(load_metadata(META_FILE)) == {"users"}


def test_ids_after_deletion():
    """Удаление средней записи не приводит к повторяющимся ID."""
    create_users()
    for name in ["A", "B", "C"]:
        command(f'insert into users values ("{name}", 1, true)')
    command("delete from users where ID=2")
    command('insert into users values ("D", 2, false)')
    assert [row["ID"] for row in load_table_data("users")] == [1, 3, 4]


def test_update_and_delete_all_matches():
    """Мутации обрабатывают каждую подходящую запись."""
    create_users()
    for name in ["A", "B"]:
        command(f'insert into users values ("{name}", 1, true)')
    command("update users set age=2, is_active=false where age=1")
    assert all(row["age"] == 2 for row in load_table_data("users"))
    command("delete from users where is_active=false")
    assert load_table_data("users") == []


def test_drop_and_recreate():
    """Повторно созданная таблица не получает старые записи."""
    create_users()
    command('insert into users values ("A", 1, true)')
    command("drop_table users")
    assert not os.path.exists("data/users.json")
    create_users()
    assert load_table_data("users") == []


def test_missing_and_corrupt_data():
    """Повреждённый файл не перезаписывается при ошибочной операции."""
    assert load_metadata("absent.json") == {}
    assert load_table_data("absent") == []
    create_users()
    with open("data/users.json", "w", encoding="utf-8") as file:
        file.write("{bad json")
    assert command('insert into users values ("A", 1, true)') is DB_ERROR
    with open("data/users.json", encoding="utf-8") as file:
        assert file.read() == "{bad json"
    assert command("info missing") is DB_ERROR
    save_table_data("users", [{"ID": 1}])
    assert command("select from users") is DB_ERROR


def test_id_only_table():
    """Явный ID не дублируется и не передаётся при вставке."""
    metadata = create_table({}, "ids", ["ID:int"])
    assert insert(metadata, "ids", []) == [{"ID": 1}]

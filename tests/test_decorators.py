import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from primitive_db.core import _select_cache, select, validate_name
from primitive_db.decorators import (
    CANCELLED,
    DB_ERROR,
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.engine import process_command
from primitive_db.utils import load_metadata


class DecoratorTests(unittest.TestCase):
    def test_errors_and_nested_calls(self):
        for error, message in [
            (KeyError("x"), "Таблица или столбец"),
            (ValueError("bad"), "Ошибка валидации"),
            (FileNotFoundError(), "Файл данных не найден"),
            (OSError("disk"), "Ошибка работы с файлом"),
            (RuntimeError("unexpected"), "непредвиденная ошибка"),
        ]:

            @handle_db_errors
            def inner():
                raise error

            continued = Mock()

            @handle_db_errors
            def outer():
                inner()
                continued()

            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertIs(outer(), DB_ERROR)
            self.assertIn(message, output.getvalue())
            self.assertEqual(len(output.getvalue().splitlines()), 1)
            continued.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIs(validate_name("../bad"), DB_ERROR)

    def test_wraps_and_confirmation(self):
        called = Mock(return_value=42)

        @confirm_action("тест")
        def operation():
            """Документация."""
            return called()

        self.assertEqual(operation.__name__, "operation")
        self.assertEqual(operation.__doc__, "Документация.")
        for answer in ["n", "", "yes", "Y"]:
            with patch("builtins.input", return_value=answer):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertIs(operation(), CANCELLED)
        called.assert_not_called()
        with patch("builtins.input", return_value="y"):
            self.assertEqual(operation(), 42)
        called.assert_called_once()

    def test_timing_and_return(self):
        @log_time
        def sample(value):
            return value

        with patch("primitive_db.decorators.time.monotonic", side_effect=[1, 1.125]):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(sample(12), 12)
        self.assertEqual(
            output.getvalue(), "Функция sample выполнилась за 0.125 секунд\n"
        )

    def test_closure_hits_isolation_and_failures(self):
        cacher = create_cacher()
        calculate = Mock(return_value=[])
        self.assertEqual(cacher("key", calculate), [])
        self.assertEqual(cacher("key", calculate), [])
        calculate.assert_called_once()
        create_cacher()("key", calculate)
        self.assertEqual(calculate.call_count, 2)
        failure = Mock(side_effect=ValueError("bad"))
        with self.assertRaises(ValueError):
            cacher("failed", failure)
        self.assertEqual(cacher("failed", lambda: 3), 3)
        self.assertIs(cacher("sentinel", lambda: DB_ERROR), DB_ERROR)
        self.assertEqual(cacher("sentinel", lambda: 4), 4)

    def test_select_cache_is_fresh_and_protected(self):
        _select_cache.clear()
        rows = [{"ID": 1, "age": 28}]
        with contextlib.redirect_stdout(io.StringIO()):
            with patch("primitive_db.core.matches", return_value=True) as matches:
                first = select(rows, {"age": 28})
                first[0]["age"] = 99
                self.assertEqual(select(rows, {"age": 28})[0]["age"], 28)
                matches.assert_called_once()
            rows[0]["age"] = 29
            self.assertEqual(select(rows, {"age": 28}), [])
            self.assertEqual(select(rows, {"age": 29}), rows)
            self.assertEqual(select(rows, {"age": True}), [])


class DecoratorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.previous = Path.cwd()
        self.directory = tempfile.TemporaryDirectory()
        os.chdir(self.directory.name)
        self.command("create_table demo name:str age:int")
        self.command('insert into demo values ("Ann", 28)')

    def tearDown(self):
        os.chdir(self.previous)
        self.directory.cleanup()

    def command(self, text):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = process_command(load_metadata("db_meta.json"), text)
        return result, output.getvalue()

    def test_cancel_keeps_files_and_has_no_success_message(self):
        metadata = Path("db_meta.json").read_bytes()
        records = Path("data/demo.json").read_bytes()
        for command in ["delete from demo where ID=1", "drop_table demo"]:
            with patch("builtins.input", return_value="n"):
                result, output = self.command(command)
            self.assertIs(result, CANCELLED)
            self.assertNotIn("успешно", output)
            self.assertEqual(Path("db_meta.json").read_bytes(), metadata)
            self.assertEqual(Path("data/demo.json").read_bytes(), records)

    def test_error_does_not_overwrite_existing_table(self):
        records = Path("data/demo.json").read_bytes()
        result, output = self.command("create_table demo name:str")
        self.assertIs(result, DB_ERROR)
        self.assertEqual(output.count("Ошибка валидации"), 1)
        self.assertEqual(Path("data/demo.json").read_bytes(), records)

    def test_queries_after_mutations_and_recreation(self):
        self.command("select from demo")
        self.command("update demo set age=29 where ID=1")
        self.assertIn("29", self.command("select from demo")[1])
        self.command('insert into demo values ("Bob", 30)')
        self.assertIn("Bob", self.command("select from demo")[1])
        with patch("builtins.input", return_value="y"):
            self.command("delete from demo where ID=1")
            self.assertNotIn("Ann", self.command("select from demo")[1])
            self.command("drop_table demo")
        self.command("create_table demo name:str age:int")
        self.assertIn("Записи не найдены", self.command("select from demo")[1])


if __name__ == "__main__":
    unittest.main()

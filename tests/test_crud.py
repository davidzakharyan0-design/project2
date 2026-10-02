import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from primitive_db.core import create_table, insert
from primitive_db.decorators import DB_ERROR
from primitive_db.engine import process_command
from primitive_db.parser import parse_command, parse_set, parse_where
from primitive_db.utils import load_metadata, load_table_data, save_table_data


class CrudTests(unittest.TestCase):
    def setUp(self):
        confirmation = patch("builtins.input", return_value="y")
        confirmation.start()
        self.addCleanup(confirmation.stop)
        self.previous = Path.cwd()
        self.directory = tempfile.TemporaryDirectory()
        os.chdir(self.directory.name)

    def tearDown(self):
        os.chdir(self.previous)
        self.directory.cleanup()

    def command(self, text):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.last_result = process_command(load_metadata("db_meta.json"), text)
        return output.getvalue()

    def create_users(self):
        self.command("create_table users name:str age:int is_active:bool")

    def test_crud_and_persistence(self):
        self.create_users()
        self.command('insert into users values ("Sergei", 28, true)')
        self.assertIn("Sergei", self.command("select from users where age=28"))
        self.command('update users set age=29 where name="Sergei"')
        self.assertEqual(load_table_data("users")[0]["age"], 29)
        result = subprocess.run(
            [sys.executable, "-m", "primitive_db.main"],
            input="select from users\nexit\n",
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("Sergei", result.stdout)
        self.assertIn("29", result.stdout)
        self.command("delete from users where ID=1")
        self.assertEqual(load_table_data("users"), [])
        self.assertIn("Количество записей: 0", self.command("info users"))

    def test_parser_quotes_and_types(self):
        self.create_users()
        self.command('insert into users values ("A, B where = test", -2, false)')
        self.assertEqual(load_table_data("users")[0]["name"], "A, B where = test")
        self.assertEqual(parse_where('name = "28"'), {"name": "28"})
        self.assertEqual(
            parse_set("age=3, is_active=true"), {"age": 3, "is_active": True}
        )
        self.assertEqual(parse_where("name='O\\'Brien'"), {"name": "O'Brien"})
        self.assertEqual(
            parse_command("update t set where=2 where ID=1")[2], {"where": 2}
        )

    def test_invalid_commands_do_not_change_data(self):
        self.create_users()
        self.command('insert into users values ("Sergei", 28, true)')
        before = Path("data/users.json").read_bytes()
        for command in [
            'insert into users values ("Bad", true, false)',
            'insert into users values ("Bad", "28", false)',
            'insert into users values ("Bad", 2)',
            'insert into users values ("Bad", 2, 1)',
            "update users set ID=2 where ID=1",
            'update users set age="bad" where ID=1',
            "update users set unknown=2 where ID=1",
            "select from users where missing=1",
            "delete from users where ID=true",
            "delete from users",
            "insert into users values (Bad, 2, true)",
            'insert into users values ("Bad", 2.5, true)',
            'insert into users values ("unterminated, 2, true)',
        ]:
            with self.subTest(command=command):
                self.command(command)
                self.assertIs(self.last_result, DB_ERROR)
                self.assertEqual(Path("data/users.json").read_bytes(), before)

    def test_ids_after_deletion(self):
        self.create_users()
        for name in ["A", "B", "C"]:
            self.command(f'insert into users values ("{name}", 1, true)')
        self.command("delete from users where ID=2")
        self.command('insert into users values ("D", 2, false)')
        self.assertEqual([row["ID"] for row in load_table_data("users")], [1, 3, 4])

    def test_update_and_delete_all_matches(self):
        self.create_users()
        for name in ["A", "B"]:
            self.command(f'insert into users values ("{name}", 1, true)')
        self.command("update users set age=2, is_active=false where age=1")
        self.assertTrue(all(row["age"] == 2 for row in load_table_data("users")))
        self.command("delete from users where is_active=false")
        self.assertEqual(load_table_data("users"), [])

    def test_drop_and_recreate(self):
        self.create_users()
        self.command('insert into users values ("A", 1, true)')
        self.command("drop_table users")
        self.assertFalse(Path("data/users.json").exists())
        self.create_users()
        self.assertEqual(load_table_data("users"), [])

    def test_missing_and_corrupt_data(self):
        self.assertEqual(load_metadata("absent.json"), {})
        self.assertEqual(load_table_data("absent"), [])
        self.create_users()
        Path("data/users.json").write_text("{bad json")
        self.command('insert into users values ("A", 1, true)')
        self.assertIs(self.last_result, DB_ERROR)
        self.assertEqual(Path("data/users.json").read_text(), "{bad json")
        self.command("info missing")
        self.assertIs(self.last_result, DB_ERROR)
        save_table_data("users", [{"ID": 1}])
        self.command("select from users")
        self.assertIs(self.last_result, DB_ERROR)

    def test_insert_signature_and_id_only_table(self):
        metadata = create_table({}, "ids", ["ID:int"])
        self.assertEqual(insert(metadata, "ids", []), [{"ID": 1}])


if __name__ == "__main__":
    unittest.main()

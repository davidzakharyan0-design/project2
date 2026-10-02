"""Имена файлов, типы и настройки учебной базы данных."""

META_FILE = "db_meta.json"
DATA_DIR = "data"
FILE_ENCODING = "utf-8"
JSON_INDENT = 4
ID_COLUMN = "ID"
ID_DEFINITION = "ID:int"
VALID_TYPES = {"int", "str", "bool"}
PYTHON_TYPES = {"int": int, "str": str, "bool": bool}
CACHE_LIMIT = 256
CONFIRMATION_ANSWER = "y"
DB_ERROR = object()
CANCELLED = object()
PUNCTUATION = "(),=:"
ASSIGNMENT_SIZE = 3  # Имя, знак равенства (или двоеточие), значение.
ASSIGNMENT_STEP = 4  # Три токена присваивания и разделяющая запятая.
KNOWN_COMMANDS = {
    "create_table",
    "drop_table",
    "list_tables",
    "help",
    "exit",
    "insert",
    "select",
    "update",
    "delete",
    "info",
}
STRING_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}

"""Разбор команд с сохранением кавычек у строковых значений."""

import ast
import re

TOKEN = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[\w+-]+|[(),=:]""")


def tokenize(text):
    tokens = []
    position = 0
    for match in TOKEN.finditer(text):
        if text[position : match.start()].strip():
            raise ValueError("Некорректное значение: проверьте синтаксис команды.")
        tokens.append(match.group())
        position = match.end()
    if text[position:].strip():
        raise ValueError("Некорректное значение: проверьте кавычки и символы.")
    return tokens


def parse_value(token):
    if token.startswith(('"', "'")):
        try:
            return ast.literal_eval(token)
        except (SyntaxError, ValueError) as error:
            raise ValueError(f"Некорректная строка: {token}.") from error
    if token.lower() in {"true", "false"}:
        return token.lower() == "true"
    if re.fullmatch(r"[+-]?[0-9]+", token):
        return int(token)
    raise ValueError(f"Некорректное значение: {token}. Строки заключайте в кавычки.")


def parse_values(tokens):
    if not tokens:
        return []
    if len(tokens) % 2 == 0 or any(t != "," for t in tokens[1::2]):
        raise ValueError("Некорректное значение: разделяйте значения запятыми.")
    return [parse_value(token) for token in tokens[::2]]


def parse_where(text):
    tokens = tokenize(text)
    if len(tokens) != 3 or tokens[1] != "=" or not tokens[0].isidentifier():
        raise ValueError("Некорректное условие. Формат: столбец = значение.")
    return {tokens[0]: parse_value(tokens[2])}


def parse_set(text):
    tokens = tokenize(text)
    result = {}
    while tokens:
        if len(tokens) < 3:
            raise ValueError("Некорректный set. Формат: столбец = значение.")
        assignment = parse_where(" ".join(tokens[:3]))
        if result.keys() & assignment.keys():
            raise ValueError("Некорректное значение: повтор столбца в set.")
        result.update(assignment)
        tokens = tokens[3:]
        if tokens:
            if tokens[0] != "," or len(tokens) == 1:
                raise ValueError("Некорректный set: ожидается запятая и присваивание.")
            tokens = tokens[1:]
    if not result:
        raise ValueError("Некорректное значение: пустой set.")
    return result


def parse_command(text):
    tokens = tokenize(text)
    match tokens:
        case []:
            return None
        case ["help" | "exit" | "list_tables" as command]:
            return command, None, None, None
        case ["info" | "drop_table" as command, table]:
            return command, table, None, None
        case ["create_table", table, *columns] if columns:
            if len(columns) % 3 or any(t != ":" for t in columns[1::3]):
                raise ValueError("Формат столбцов: имя:тип имя:тип.")
            schema = [
                f"{columns[i]}:{columns[i + 2]}" for i in range(0, len(columns), 3)
            ]
            return "create_table", table, schema, None
        case ["insert", "into", table, "values", "(", *values, ")"]:
            return "insert", table, parse_values(values), None
        case ["select", "from", table]:
            return "select", table, None, None
        case ["select" | "delete" as command, "from", table, "where", *condition]:
            return command, table, None, parse_where(" ".join(condition))
        case ["update", table, "set", *rest] if "where" in rest:
            boundary = next(
                (i for i in range(3, len(rest), 4) if rest[i] == "where"),
                -1,
            )
            if boundary == -1:
                raise ValueError("Некорректный update: требуется условие where.")
            changes = parse_set(" ".join(rest[:boundary]))
            condition = parse_where(" ".join(rest[boundary + 1 :]))
            return "update", table, changes, condition
    known = {
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
    if tokens[0] not in known:
        raise ValueError(f"Функции {tokens[0]} нет. Попробуйте снова.")
    raise ValueError("Некорректное значение: аргументы команды. Введите help.")

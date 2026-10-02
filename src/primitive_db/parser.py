"""Разбор команд, строк в кавычках и типизированных значений."""

import shlex

from primitive_db.constants import (
    ASSIGNMENT_SIZE,
    ASSIGNMENT_STEP,
    KNOWN_COMMANDS,
    PUNCTUATION,
    STRING_ESCAPES,
)


def split_unquoted(text):
    """Разбивает часть команды без строковых литералов через shlex."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    tokens = []
    for token in lexer:
        if all(character in PUNCTUATION for character in token):
            tokens.extend(token)
        else:
            tokens.append(token)
    return tokens


def tokenize(text):
    """Сохраняет строки с кавычками, остальные части разбирает через shlex."""
    tokens = []
    start = 0
    position = 0
    while position < len(text):
        if text[position] not in {"'", '"'}:
            position += 1
            continue
        tokens.extend(split_unquoted(text[start:position]))
        quote = text[position]
        start = position
        position += 1
        while position < len(text):
            if text[position] == "\\":
                position += 2
            elif text[position] == quote:
                position += 1
                tokens.append(text[start:position])
                start = position
                break
            else:
                position += 1
        else:
            raise ValueError("Некорректное значение: незакрытая строка.")
    tokens.extend(split_unquoted(text[start:]))
    return tokens


def parse_string(token):
    """Читает строку, поддерживая экранированные кавычки и переносы строк."""
    if len(token) < 2 or token[-1] != token[0]:
        raise ValueError("Некорректное значение: незакрытая строка.")
    result = []
    position = 1
    while position < len(token) - 1:
        character = token[position]
        if character == token[0]:
            raise ValueError("Некорректная кавычка внутри строки.")
        if character == "\\":
            position += 1
            if position >= len(token) - 1 or token[position] not in STRING_ESCAPES:
                raise ValueError("Некорректная escape-последовательность.")
            character = STRING_ESCAPES[token[position]]
        result.append(character)
        position += 1
    return "".join(result)


def parse_value(token):
    """Возвращает str, int или bool, не выполняя пользовательский код."""
    if token.startswith(('"', "'")):
        return parse_string(token)
    if token.lower() in {"true", "false"}:
        return token.lower() == "true"
    digits = token[1:] if token.startswith(("+", "-")) else token
    if digits and all(character in "0123456789" for character in digits):
        return int(token)
    raise ValueError(f"Некорректное значение: {token}. Строки заключайте в кавычки.")


def parse_values(tokens):
    """Преобразует разделённые запятыми токены в список значений."""
    if not tokens:
        return []
    if len(tokens) % 2 == 0 or any(t != "," for t in tokens[1::2]):
        raise ValueError("Некорректное значение: разделяйте значения запятыми.")
    return [parse_value(token) for token in tokens[::2]]


def parse_where(text):
    """Преобразует условие равенства в словарь из одного поля."""
    tokens = tokenize(text)
    if (
        len(tokens) != ASSIGNMENT_SIZE
        or tokens[1] != "="
        or not tokens[0].isidentifier()
    ):
        raise ValueError("Некорректное условие. Формат: столбец = значение.")
    return {tokens[0]: parse_value(tokens[2])}


def parse_set(text):
    """Разбирает присваивания, запрещая повторяющиеся поля."""
    tokens = tokenize(text)
    result = {}
    while tokens:
        if len(tokens) < ASSIGNMENT_SIZE:
            raise ValueError("Некорректный set. Формат: столбец = значение.")
        assignment = parse_where(" ".join(tokens[:ASSIGNMENT_SIZE]))
        if result.keys() & assignment.keys():
            raise ValueError("Некорректное значение: повтор столбца в set.")
        result.update(assignment)
        tokens = tokens[ASSIGNMENT_SIZE:]
        if tokens:
            if tokens[0] != "," or len(tokens) == 1:
                raise ValueError("Некорректный set: ожидается запятая и присваивание.")
            tokens = tokens[1:]
    if not result:
        raise ValueError("Некорректное значение: пустой set.")
    return result


def parse_command(text):
    """Возвращает команду, таблицу, значения и условие из строки."""
    tokens = tokenize(text)
    match tokens:
        case []:
            return None
        case ["help" | "exit" | "list_tables" as command]:
            return command, None, None, None
        case ["info" | "drop_table" as command, table]:
            return command, table, None, None
        case ["create_table", table, *columns] if columns:
            if len(columns) % ASSIGNMENT_SIZE or any(
                t != ":" for t in columns[1::ASSIGNMENT_SIZE]
            ):
                raise ValueError("Формат столбцов: имя:тип имя:тип.")
            schema = [
                f"{columns[i]}:{columns[i + 2]}"
                for i in range(0, len(columns), ASSIGNMENT_SIZE)
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
                (
                    i
                    for i in range(ASSIGNMENT_SIZE, len(rest), ASSIGNMENT_STEP)
                    if rest[i] == "where"
                ),
                -1,
            )
            if boundary == -1:
                raise ValueError("Некорректный update: требуется условие where.")
            changes = parse_set(" ".join(rest[:boundary]))
            condition = parse_where(" ".join(rest[boundary + 1 :]))
            return "update", table, changes, condition
    if tokens[0] not in KNOWN_COMMANDS:
        raise ValueError(f"Функции {tokens[0]} нет. Попробуйте снова.")
    raise ValueError("Некорректное значение: аргументы команды. Введите help.")

import json

from primitive_db.constants import ID_COLUMN, ID_DEFINITION, PYTHON_TYPES, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data


@handle_db_errors
def validate_name(name):
    """Проверяет допустимость имени таблицы или столбца."""
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f"Некорректное значение: {name}. Попробуйте снова.")


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Добавляет проверенную схему таблицы с автоматическим ID."""
    validate_name(table_name)

    if table_name in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" уже существует.')

    if not columns:
        raise ValueError(
            "Некорректное значение: список столбцов пуст. Попробуйте снова."
        )

    result_columns = [ID_DEFINITION]
    seen_names = set()

    for column in columns:
        if not isinstance(column, str) or column.count(":") != 1:
            raise ValueError(f"Некорректное значение: {column}. Попробуйте снова.")

        name, data_type = column.split(":")
        validate_name(name)

        if data_type not in VALID_TYPES:
            raise ValueError(
                f"Некорректное значение: {column}. "
                "Допустимые типы: int, str, bool. Попробуйте снова."
            )

        if name in seen_names:
            raise ValueError(
                f"Некорректное значение: повтор столбца {name}. Попробуйте снова."
            )

        seen_names.add(name)

        if name == ID_COLUMN:
            if data_type != "int":
                raise ValueError(
                    "Некорректное значение: ID должен иметь тип int. Попробуйте снова."
                )
            continue

        result_columns.append(column)

    metadata[table_name] = result_columns
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет схему существующей таблицы после подтверждения."""
    validate_name(table_name)

    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')

    del metadata[table_name]
    return metadata


@handle_db_errors
def list_tables(metadata):
    """Возвращает имена таблиц в алфавитном порядке."""
    return sorted(metadata)


@handle_db_errors
def get_schema(metadata, table_name):
    """Возвращает отображение имён столбцов в типы данных."""
    validate_name(table_name)
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    return dict(column.split(":") for column in metadata[table_name])


@handle_db_errors
def validate_fields(schema, fields, allow_id=True):
    """Проверяет наличие полей и точное соответствие их типов."""
    for name, value in fields.items():
        if name not in schema:
            raise ValueError(f"Некорректное значение: столбца {name} нет.")
        if name == ID_COLUMN and not allow_id:
            raise ValueError("Некорректное значение: ID изменять нельзя.")
        if type(value) is not PYTHON_TYPES[schema[name]]:
            raise ValueError(
                f"Некорректное значение: {value!r}. "
                f"Столбец {name} требует тип {schema[name]}."
            )


@handle_db_errors
def validate_table_data(schema, table_data):
    """Проверяет структуру записей и уникальность положительных ID."""
    ids = set()
    for row in table_data:
        if row.keys() != schema.keys():
            raise ValueError("Структура сохранённой записи не совпадает со схемой.")
        validate_fields(schema, row)
        if row[ID_COLUMN] < 1 or row[ID_COLUMN] in ids:
            raise ValueError("Некорректный или повторяющийся ID в файле данных.")
        ids.add(row[ID_COLUMN])


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Загружает записи и добавляет проверенную строку с новым ID."""
    schema = get_schema(metadata, table_name)
    columns = [name for name in schema if name != ID_COLUMN]
    if len(values) != len(columns):
        raise ValueError(f"Ожидается значений: {len(columns)} (без ID).")
    record = dict(zip(columns, values, strict=True))
    validate_fields(schema, record)
    table_data = load_table_data(table_name)
    validate_table_data(schema, table_data)
    new_id = max((row[ID_COLUMN] for row in table_data), default=0) + 1
    table_data.append({ID_COLUMN: new_id, **record})
    return table_data


@handle_db_errors
def matches(row, where_clause):
    """Проверяет совпадение записи с условием, включая тип значения."""
    return all(
        name in row and type(row[name]) is type(value) and row[name] == value
        for name, value in where_clause.items()
    )


_select_cache = create_cacher()


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    # Снимок данных в ключе защищает от устаревших результатов после
    # insert/update/delete, перезапуска таблицы и внешней правки JSON.
    """Возвращает независимую копию выборки, используя кэш запросов."""
    key = json.dumps([table_data, where_clause], sort_keys=True, ensure_ascii=False)

    def calculate():
        """Вычисляет выборку для отсутствующего в кэше запроса."""
        rows = (
            table_data
            if where_clause is None
            else [row for row in table_data if matches(row, where_clause)]
        )
        return [dict(row) for row in rows]

    # Вызывающий код не может испортить сохранённый результат.
    return [dict(row) for row in _select_cache(key, calculate)]


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновляет все подходящие записи, сохраняя их ID."""
    if ID_COLUMN in set_clause:
        raise ValueError("Некорректное значение: ID изменять нельзя.")
    return [
        {**row, **set_clause} if matches(row, where_clause) else dict(row)
        for row in table_data
    ]


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удаляет подходящие записи после подтверждения пользователя."""
    return [row for row in table_data if not matches(row, where_clause)]

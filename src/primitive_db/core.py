from primitive_db.utils import load_table_data

SUPPORTED_TYPES = {"int", "str", "bool"}


def validate_name(name):
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f"Некорректное значение: {name}. Попробуйте снова.")


def create_table(metadata, table_name, columns):
    validate_name(table_name)

    if table_name in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" уже существует.')

    if not columns:
        raise ValueError(
            "Некорректное значение: список столбцов пуст. Попробуйте снова."
        )

    result_columns = ["ID:int"]
    seen_names = set()

    for column in columns:
        if not isinstance(column, str) or column.count(":") != 1:
            raise ValueError(f"Некорректное значение: {column}. Попробуйте снова.")

        name, data_type = column.split(":")
        validate_name(name)

        if data_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Некорректное значение: {column}. "
                "Допустимые типы: int, str, bool. Попробуйте снова."
            )

        if name in seen_names:
            raise ValueError(
                f"Некорректное значение: повтор столбца {name}. Попробуйте снова."
            )

        seen_names.add(name)

        if name == "ID":
            if data_type != "int":
                raise ValueError(
                    "Некорректное значение: ID должен иметь тип int. Попробуйте снова."
                )
            continue

        result_columns.append(column)

    metadata[table_name] = result_columns
    return metadata


def drop_table(metadata, table_name):
    validate_name(table_name)

    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')

    del metadata[table_name]
    return metadata


def list_tables(metadata):
    return sorted(metadata)


PYTHON_TYPES = {"int": int, "str": str, "bool": bool}


def get_schema(metadata, table_name):
    validate_name(table_name)
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    return dict(column.split(":") for column in metadata[table_name])


def validate_fields(schema, fields, allow_id=True):
    for name, value in fields.items():
        if name not in schema:
            raise ValueError(f"Некорректное значение: столбца {name} нет.")
        if name == "ID" and not allow_id:
            raise ValueError("Некорректное значение: ID изменять нельзя.")
        if type(value) is not PYTHON_TYPES[schema[name]]:
            raise ValueError(
                f"Некорректное значение: {value!r}. "
                f"Столбец {name} требует тип {schema[name]}."
            )


def validate_table_data(schema, table_data):
    ids = set()
    for row in table_data:
        if row.keys() != schema.keys():
            raise ValueError("Структура сохранённой записи не совпадает со схемой.")
        validate_fields(schema, row)
        if row["ID"] < 1 or row["ID"] in ids:
            raise ValueError("Некорректный или повторяющийся ID в файле данных.")
        ids.add(row["ID"])


def insert(metadata, table_name, values):
    schema = get_schema(metadata, table_name)
    columns = [name for name in schema if name != "ID"]
    if len(values) != len(columns):
        raise ValueError(f"Ожидается значений: {len(columns)} (без ID).")
    record = dict(zip(columns, values, strict=True))
    validate_fields(schema, record)
    table_data = load_table_data(table_name)
    validate_table_data(schema, table_data)
    new_id = max((row["ID"] for row in table_data), default=0) + 1
    table_data.append({"ID": new_id, **record})
    return table_data


def matches(row, where_clause):
    return all(
        name in row and type(row[name]) is type(value) and row[name] == value
        for name, value in where_clause.items()
    )


def select(table_data, where_clause=None):
    if where_clause is None:
        return list(table_data)
    return [row for row in table_data if matches(row, where_clause)]


def update(table_data, set_clause, where_clause):
    if "ID" in set_clause:
        raise ValueError("Некорректное значение: ID изменять нельзя.")
    return [
        {**row, **set_clause} if matches(row, where_clause) else dict(row)
        for row in table_data
    ]


def delete(table_data, where_clause):
    return [row for row in table_data if not matches(row, where_clause)]

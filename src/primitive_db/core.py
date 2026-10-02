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

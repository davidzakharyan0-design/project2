import json
from pathlib import Path


def load_metadata(filepath):
    try:
        with open(filepath, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Метаданные должны быть JSON-объектом.")

    for table_name, columns in data.items():
        if not isinstance(columns, list):
            raise ValueError(f'Некорректная структура таблицы "{table_name}".')
        if not all(isinstance(column, str) for column in columns):
            raise ValueError(f'Некорректные столбцы таблицы "{table_name}".')

    return data


def save_metadata(filepath, data):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def table_path(table_name):
    if not isinstance(table_name, str) or not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}.")
    return Path("data") / f"{table_name}.json"


def load_table_data(table_name):
    try:
        with table_path(table_name).open(encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError(f'Некорректные данные таблицы "{table_name}".')
    return data


def save_table_data(table_name, data):
    path = table_path(table_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_metadata(path, data)


def delete_table_data(table_name):
    table_path(table_name).unlink(missing_ok=True)

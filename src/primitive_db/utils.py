import json
import os

from primitive_db.constants import DATA_DIR, FILE_ENCODING, JSON_INDENT


def load_metadata(filepath):
    """Читает метаданные; для отсутствующего файла возвращает словарь."""
    try:
        with open(filepath, encoding=FILE_ENCODING) as file:
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
    """Сохраняет переданные данные в JSON-файл."""
    with open(filepath, "w", encoding=FILE_ENCODING) as file:
        json.dump(data, file, ensure_ascii=False, indent=JSON_INDENT)
        file.write("\n")


def table_path(table_name):
    """Возвращает безопасный относительный путь к файлу таблицы."""
    if not isinstance(table_name, str) or not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}.")
    return os.path.join(DATA_DIR, f"{table_name}.json")


def load_table_data(table_name):
    """Читает список записей таблицы или возвращает пустой список."""
    try:
        with open(table_path(table_name), encoding=FILE_ENCODING) as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError(f'Некорректные данные таблицы "{table_name}".')
    return data


def save_table_data(table_name, data):
    """Создаёт каталог данных и сохраняет записи таблицы."""
    path = table_path(table_name)
    os.makedirs(DATA_DIR, exist_ok=True)
    save_metadata(path, data)


def delete_table_data(table_name):
    """Удаляет файл таблицы, если он существует."""
    try:
        os.remove(table_path(table_name))
    except FileNotFoundError:
        pass
